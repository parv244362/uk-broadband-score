"""EE Broadband scraper implementation with contract switching."""

import re
from typing import List, Dict, Any, Optional
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from src.scrapers.base_scraper import BaseScraper
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class EEScraper(BaseScraper):
    """
    Scraper for EE Broadband.
    
    Handles:
    - Multiple contract length tabs (12 and 24 months)
    - Card-based product layouts
    - Active panel detection for tabbed interfaces
    - Speed guarantee extraction
    - Price rise information
    """
    
    # CTA button variations
    CTA_SELECTORS = [
        "button:has-text('See your deals')",
        "a:has-text('See your deals')",
        "button:has-text('See deals')",
        "a:has-text('See deals')",
        "button:has-text('Check availability')",
        "a:has-text('Check availability')",
        "button:has-text('See broadband deals')",
        "a:has-text('See broadband deals')",
    ]
    
    # Product card selectors
    CARD_SELECTORS = [
    "[data-testid^='ProductSelectPanel_']"
    ]

    
    @property
    def provider_name(self) -> str:
        return "ee"
    
    async def _click_see_deals(self) -> bool:
        """Click 'See deals' CTA button."""
        for sel in self.CTA_SELECTORS:
            btn = self.page.locator(sel).first
            try:
                if await btn.is_visible(timeout=2500):
                    await btn.click()
                    await self.page.wait_for_timeout(4000)
                    logger.info(f"{self.provider_name.upper()}: Clicked 'See deals' CTA")
                    return True
            except Exception:
                continue
        return False
    

    async def _switch_to_12_month(self) -> bool:
        """Switch to 12-month contract tab."""
        selectors = [
            "button:has-text('12 months')",
            "button:has-text('12 month')",
            "a:has-text('12 months')",
            "a:has-text('12 month')",
            "div[role='tab']:has-text('12')",
        ]
        
        for sel in selectors:
            tab = self.page.locator(sel).first
            try:
                if await tab.is_visible(timeout=4000):
                    await tab.click()
                    await self.page.wait_for_timeout(8000)
                    logger.info(f"{self.provider_name.upper()}: Switched to 12-month contracts")
                    return True
            except Exception:
                continue
        
        return False
    
    async def _get_active_panel(self):
        """Get the currently active tab panel."""
        return self.page.locator("div[role='tabpanel'][aria-hidden='false']").first
    

    def extract_price(self, price_str: str) -> Optional[float]:
        """Extract numeric price from string like '£25.99'"""
        if not price_str:
            return None
        price_str = price_str.replace("£", "").replace(",", "").strip()
        try:
            return float(price_str)
        except ValueError:
            return None

    
    async def _wait_for_cards(self):
        """Wait for product cards to load in active panel."""
        try:
            await self.page.wait_for_selector(
                "div[role='tabpanel'][aria-hidden='false'] [data-testid^='ProductSelectPanel_'], "
                "div[role='tabpanel'][aria-hidden='false'] [data-testid='product-card']",
                timeout=20000,  # increase timeout
            )
            # Extra small delay to ensure inner elements load
            await self.page.wait_for_timeout(8000)
        except PlaywrightTimeoutError:
            logger.warning(f"{self.provider_name.upper()}: Timeout waiting for cards, continuing anyway")

    
    async def _parse_card(self, card, postcode: str, contract_length: int) -> Dict[str, Any]:
        """
        Parse a single product card, with retries for dynamic content loading.
        """
        try:
            retries = 3
            deal_name = None
            monthly_price = None
            download_speed = None
            upload_speed = None

            for attempt in range(retries):
                # ---------- DEAL NAME ----------
                deal_name = None
                
                # Try to get heading that contains speed + plan type
                name_elements = await card.locator("span[class*='Heading'], h3, h2").all_inner_texts()
                
                for name_text in name_elements:
                    name_text = name_text.strip()
                    # Look for something that contains Mbps and optionally a plan type
                    if re.search(r"\d+\s*-\s*\d+Mbps|\d+Mbps", name_text, re.IGNORECASE):
                        deal_name = name_text  # take the full text including Core/Standard
                        break
                    
                # Fallback: take first heading containing a known plan type
                if not deal_name:
                    for name_text in name_elements:
                        if any(k in name_text for k in ["Core", "Plus", "Essential", "Standard"]):
                            deal_name = name_text.strip()
                            break
                        
                # Last fallback: just take first heading
                if not deal_name and name_elements:
                    deal_name = name_elements[0].strip()


                # ---------- MONTHLY PRICE ----------
                price_el = card.locator("span.lc-Price-srOnly").first
                monthly_price = None
                if await price_el.count():
                    price_text = (await price_el.inner_text()).strip()
                    monthly_price = self.extract_price(price_text)

                # Fallback: old method if .lc-Price-srOnly not found
                if not monthly_price:
                    price_el_alt = card.locator("span[class*='Price'], .price, [data-testid*='Price']").first
                    if await price_el_alt.count():
                        price_text = (await price_el_alt.inner_text()).strip()
                        monthly_price = self.extract_price(price_text)

                # ---------- DOWNLOAD SPEED ----------
                download_speed = None

                if deal_name:
                    # Match number followed by 'Mbps' explicitly
                    match = re.search(r"(\d+)(?:-(\d+))?\s*Mbps", deal_name, re.IGNORECASE)
                    if match:
                        download_speed = float(match.group(1))

                # Fallback: look for speed tags like "36Mbps Speed Guarantee"
                if not download_speed:
                    speed_el = card.locator("span.lc-Tag-text:has-text('Mbps')")
                    if await speed_el.count():
                        text = await speed_el.first.inner_text()
                        match = re.search(r"(\d+)\s*Mbps", text, re.IGNORECASE)
                        if match:
                            download_speed = float(match.group(1))

                # ---------- UPLOAD SPEED ----------
                upload_el = card.locator("span.lc-Tag-text:has-text('upload')")
                if await upload_el.count():
                    txt = await upload_el.first.inner_text()
                    upload_speed = self.extract_speed(txt)

                # Check if essential data is available
                if deal_name and monthly_price and download_speed:
                    break

                # Wait a bit and retry if essential data missing
                logger.debug(f"{self.provider_name.upper()}: Retry {attempt+1} for card due to incomplete data")
                await self.page.wait_for_timeout(8000)

            # If still missing essential data, skip
            if not deal_name or not monthly_price or not download_speed:
                raw_text = await card.inner_text()
                logger.debug(f"{self.provider_name.upper()}: Skipping incomplete card. Raw text:\n{raw_text}")
                return {}

            # ---------- BUILD DEAL DICT ----------
            deal = {
                "provider": self.provider_name,
                "deal_name": deal_name or "Fibre",
                "postcode": postcode,
                "monthly_price": monthly_price,
                "contract_length": contract_length,
                "total_contract_cost": monthly_price * contract_length,
                "download_speed": download_speed,
                "upload_speed": upload_speed,
                "data_allowance": "Unlimited",
                "router_included": None,
                "installation_type": "Standard",
                "technology_type": "FTTC" if download_speed < 100 else "FTTP",
                "url": self.page.url,
                "upfront_cost": 0.0
            }

            logger.debug(
                f"{self.provider_name.upper()}: Parsed card | "
                f"name={deal_name}, download={download_speed}, upload={upload_speed}, "
                f"monthly={monthly_price}"
            )

            return deal

        except Exception as e:
            logger.warning(f"{self.provider_name.upper()}: Card parse failed: {e}", exc_info=True)
            return {}


    
    async def _scrape_cards(self, postcode: str, contract_length: int) -> List[Dict[str, Any]]:

        """Scrape all product cards in the active panel."""
        await self._wait_for_cards()
        
        deals = []
        panel = await self._get_active_panel()
        
        # Wait for results to load
        await self.page.wait_for_timeout(4000)

        # Find cards using multiple selectors
        cards = None
        for sel in self.CARD_SELECTORS:
            loc = panel.locator(sel)
            try:
                count = await loc.count()
                if count > 0:
                    cards = loc
                    logger.info(f"{self.provider_name.upper()}: Found {count} cards with selector: {sel}")
                    break
            except Exception:
                continue
        
        if cards is None:
            logger.warning(f"{self.provider_name.upper()}: No cards found")
            return deals
        
        card_count = await cards.count()
        
        for i in range(card_count):
            card = cards.nth(i)
            try:
                deal = await self._parse_card(card, postcode, contract_length)
                
                # Only add deals with essential data
                if deal.get("monthly_price") and deal.get("download_speed"):
                    deals.append(deal)
                else:
                    logger.debug(f"{self.provider_name.upper()}: Skipping incomplete deal {i + 1}")
            
            except Exception as e:
                logger.warning(f"{self.provider_name.upper()}: Failed to parse card {i + 1}: {str(e)}")
                continue
        
        return deals
    
    async def extract_deals(self) -> List[Dict[str, Any]]:
        """
        Extract deals - not used in custom scrape() implementation.
        EE requires custom navigation flow.
        """
        return []
    
    async def scrape(self, postcode: str, address: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Main scraping workflow for EE with contract switching.
        
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
            
            # Wait for results to load
            await self.page.wait_for_timeout(4000)
            
            # Enter postcode
            await self.enter_postcode(postcode)
            
            # Select address if prompted
            await self.select_address(address)
            
            # Click 'See deals' again after postcode entry
            await self._click_see_deals()

            # Wait for results to load
            await self.page.wait_for_timeout(4000)
            
            all_deals = []
            
            # Scrape 24-month contracts (default tab)
            logger.info(f"{self.provider_name.upper()}: Scraping 24-month contracts")
            deals_24 = await self._scrape_cards(postcode, contract_length=24)
            all_deals.extend(deals_24)
            
            # Wait for results to load
            await self.page.wait_for_timeout(4000)

            # Try to switch to 12-month contracts
            if await self._switch_to_12_month():
                logger.info(f"{self.provider_name.upper()}: Scraping 12-month contracts")
                deals_12 = await self._scrape_cards(postcode, contract_length=12)
                all_deals.extend(deals_12)
            else:
                logger.info(f"{self.provider_name.upper()}: 12-month tab not found or not available")

            if all_deals:
                logger.info(f"{self.provider_name.upper()}: Extracted {len(all_deals)} total deals")
                return all_deals
            
            # No deals found
            logger.warning(f"{self.provider_name.upper()}: No deals found")
            return []
        
        except Exception as e:
            logger.error(f"{self.provider_name.upper()}: Scraping failed: {str(e)}", exc_info=True)
            return []
