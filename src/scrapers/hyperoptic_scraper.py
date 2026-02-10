"""Hyperoptic scraper implementation with XPath-based card detection."""

import re
from typing import List, Dict, Any, Optional
from src.scrapers.base_scraper import BaseScraper
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class HyperopticScraper(BaseScraper):
    """
    Scraper for Hyperoptic.
    
    Handles:
    - XPath-based card detection (finds elements with both £ and Mb/Gb)
    - Text-based parsing for all data
    - Full fiber classification
    - Upload speed extraction
    - Symmetric speeds (common for fiber)
    """
    
    @property
    def provider_name(self) -> str:
        return "hyperoptic"
    
    async def _find_product_cards(self):
        """
        Find product cards using XPath.
        
        Hyperoptic's page structure varies, so we use XPath to find any element
        containing both price (£) and speed (Mb/Gb), then get its container.
        """
        xpath = (
            "xpath=//*[contains(., '£') and (contains(., 'Mb') or contains(., 'Gb'))]"
            "/ancestor::*[self::div or self::section][1]"
        )
        return self.page.locator(xpath)
    
    async def _parse_card(self, card, postcode: str) -> Optional[Dict[str, Any]]:
        """Parse a single product card from text content."""
        try:
            card_text = await card.inner_text()
        except Exception:
            return None
        
        card_text_clean = card_text.strip()
        
        # Skip cards without price indicator
        if "£" not in card_text_clean:
            return None
        
        # Extract price
        price = self.extract_price(card_text_clean)
        
        # Extract download speed
        download_speed = None
        speed_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(G|M)b", card_text_clean, re.I)
        if speed_match:
            download_speed = self.extract_speed(speed_match.group(0) + "ps")
        
        # Extract upload speed
        upload_speed = None
        upload_match = re.search(
            r"upload[^0-9]*([0-9]+(?:\.[0-9]+)?)(?:\s*)(G|M)b",
            card_text_clean,
            re.I
        )
        if upload_match:
            upload_speed = self.extract_speed(upload_match.group(1) + upload_match.group(2) + "ps")
        
        # Determine package type based on speed
        package_name = "Fibre"
        if download_speed and download_speed >= 100:
            package_name = "Full Fibre"
        
        # For Hyperoptic, if no explicit upload speed, assume symmetric
        # (Hyperoptic typically offers symmetric speeds on full fiber)
        if not upload_speed and download_speed and download_speed >= 100:
            upload_speed = download_speed
        
        deal = {
            "provider": "hyperoptic",
            "deal_name": package_name,
            "postcode": postcode,
            "monthly_price": price,
            "contract_length": 24,  # Hyperoptic standard
            "download_speed": download_speed,
            "upload_speed": upload_speed,
            "data_allowance": "Unlimited",
            "technology_type": "FTTP",  # Hyperoptic is full fiber to premises
            "url": self.page.url,
        }
        
        return deal
    
    async def extract_deals(self) -> List[Dict[str, Any]]:
        """
        Extract deals - not used in custom scrape() implementation.
        Hyperoptic requires XPath-based card detection.
        """
        return []
    
    async def scrape(self, postcode: str, address: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Main scraping workflow for Hyperoptic.
        
        Args:
            postcode: UK postcode to search
            address: Specific address (not used, auto-selects first)
            
        Returns:
            List of broadband deals
        """
        try:
            # Initialize browser
            await self.initialize_browser()
            
            # Navigate to landing page
            await self.navigate_to_page()
            logger.info(f"{self.provider_name.upper()}: On landing page")
            
            # Handle cookies
            await self.handle_cookies()
            
            # Enter postcode
            await self.enter_postcode(postcode)
            
            # Select address if prompted
            await self.select_address(address)
            
            # Wait for results to load
            await self.page.wait_for_timeout(1500)
            
            # Find product cards using XPath
            cards = await self._find_product_cards()
            card_count = await cards.count()
            
            logger.info(f"{self.provider_name.upper()}: Found {card_count} potential product cards")
            
            deals = []
            
            for i in range(card_count):
                card = cards.nth(i)
                
                try:
                    deal = await self._parse_card(card, postcode)
                    
                    # Only add deals with essential data
                    if deal and deal.get("monthly_price") and deal.get("download_speed"):
                        deals.append(deal)
                    else:
                        logger.debug(f"{self.provider_name.upper()}: Skipping incomplete card {i + 1}")
                
                except Exception as e:
                    logger.warning(f"{self.provider_name.upper()}: Failed to parse card {i + 1}: {str(e)}")
                    continue
            
            if deals:
                logger.info(f"{self.provider_name.upper()}: Extracted {len(deals)} deals")
                return deals
            
            # No deals found
            logger.warning(f"{self.provider_name.upper()}: No deals found")
            return []
        
        except Exception as e:
            logger.error(f"{self.provider_name.upper()}: Scraping failed: {str(e)}", exc_info=True)
            return []
