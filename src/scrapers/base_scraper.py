"""Base scraper class with common functionality for all provider scrapers."""

import json
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any

from playwright.async_api import async_playwright, Browser, Page, TimeoutError

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class BaseScraper(ABC):
    """Abstract base class for provider-specific scrapers."""
    
    def __init__(self, headless: bool = True):
        """
        Initialize the scraper.
        
        Args:
            headless: Run browser in headless mode
        """
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.playwright = None
        
        # Load configuration
        self.config = self._load_config()
        self.settings = self._load_settings()
        self.provider_config = self._get_provider_config()
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name identifier (e.g., 'sky', 'bt')."""
        pass
    
    def _load_config(self) -> Dict[str, Any]:
        """Load provider configurations from JSON."""
        config_path = Path(__file__).parent.parent.parent / "config" / "providers.json"
        with open(config_path, "r") as f:
            return json.load(f)
    
    def _load_settings(self) -> Dict[str, Any]:
        """Load application settings from JSON."""
        settings_path = Path(__file__).parent.parent.parent / "config" / "settings.json"
        with open(settings_path, "r") as f:
            return json.load(f)
    
    def _get_provider_config(self) -> Dict[str, Any]:
        """Get configuration for this specific provider."""
        return self.config.get(self.provider_name, {})
    
    async def initialize_browser(self) -> None:
        """Initialize Playwright and browser instance."""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            
            # Create context with settings
            context = await self.browser.new_context(
                viewport={
                    "width": self.settings["scraping"]["viewport"]["width"],
                    "height": self.settings["scraping"]["viewport"]["height"]
                },
                user_agent=self.settings["browser"]["user_agent"],
                locale=self.settings["browser"]["locale"],
                timezone_id=self.settings["browser"]["timezone"]
            )
            
            self.page = await context.new_page()
            logger.info(f"{self.provider_name.upper()}: Browser initialized")
            
        except Exception as e:
            logger.error(f"{self.provider_name.upper()}: Failed to initialize browser: {str(e)}")
            raise
    
    async def close(self) -> None:
        """Close browser and cleanup resources."""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info(f"{self.provider_name.upper()}: Browser closed")
        except Exception as e:
            logger.error(f"{self.provider_name.upper()}: Error closing browser: {str(e)}")
    
    async def navigate_to_page(self, url: Optional[str] = None) -> None:
        """Navigate to the provider's page."""
        target_url = url or self.provider_config.get("url")
        
        try:
            logger.info(f"{self.provider_name.upper()}: Navigating to {target_url}")
            await self.page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
            await self.page.wait_for_load_state("networkidle", timeout=30000)
            logger.info(f"{self.provider_name.upper()}: Page loaded successfully")
        except TimeoutError:
            logger.warning(f"{self.provider_name.upper()}: Page load timeout, continuing anyway")
        except Exception as e:
            logger.error(f"{self.provider_name.upper()}: Navigation failed: {str(e)}")
            raise
    
    async def handle_cookies(self) -> bool:
        """Handle cookie consent banner."""
        try:
            logger.info(f"{self.provider_name.upper()}: Looking for cookie banner...")
            
            # Get cookie selectors from config
            cookie_selectors = self.provider_config.get("cookie_selectors", [])
            
            for selector in cookie_selectors:
                try:
                    # Wait for button to appear
                    button = await self.page.wait_for_selector(
                        selector,
                        timeout=5000,
                        state="visible"
                    )
                    
                    if button:
                        await button.click()
                        logger.info(f"{self.provider_name.upper()}: Cookies accepted successfully")
                        await self.page.wait_for_timeout(1000)
                        return True
                        
                except TimeoutError:
                    continue
            
            logger.warning(f"{self.provider_name.upper()}: Cookie banner not found, continuing...")
            return False
            
        except Exception as e:
            logger.warning(f"{self.provider_name.upper()}: Cookie handling failed: {str(e)}")
            return False
    
    async def enter_postcode(self, postcode: str) -> bool:
        """Enter postcode in the input field."""
        try:
            logger.info(f"{self.provider_name.upper()}: Entering postcode {postcode}")
            
            input_selector = self.provider_config.get("postcode_input_selector")
            submit_selector = self.provider_config.get("postcode_submit_selector")
            
            # Wait for input field
            await self.page.wait_for_selector(input_selector, timeout=10000)
            
            # Clear and enter postcode
            await self.page.fill(input_selector, "")
            await self.page.fill(input_selector, postcode)
            await self.page.wait_for_timeout(500)
            
            # Submit
            await self.page.click(submit_selector)
            logger.info(f"{self.provider_name.upper()}: Postcode submitted")
            
            # Wait for results
            await self.page.wait_for_timeout(2000)
            return True
            
        except Exception as e:
            logger.error(f"{self.provider_name.upper()}: Failed to enter postcode: {str(e)}")
            return False
    
    async def select_address(self, preferred_address: Optional[str] = None) -> bool:
        """Select address from dropdown/list."""
        try:
            logger.info(f"{self.provider_name.upper()}: Selecting address...")
            
            address_selector = self.provider_config.get("address_dropdown_selector")
            
            # Wait for address selector
            await self.page.wait_for_selector(address_selector, timeout=10000)
            
            if preferred_address:
                # Try to select specific address
                await self.page.select_option(address_selector, label=preferred_address)
                logger.info(f"{self.provider_name.upper()}: Selected address: {preferred_address}")
            else:
                # Select first available address
                options = await self.page.query_selector_all(f"{address_selector} option")
                if len(options) > 1:
                    await self.page.select_option(address_selector, index=1)
                    logger.info(f"{self.provider_name.upper()}: Selected first available address")
            
            await self.page.wait_for_timeout(2000)
            return True
            
        except Exception as e:
            logger.error(f"{self.provider_name.upper()}: Failed to select address: {str(e)}")
            return False
    
    def extract_price(self, text: str) -> Optional[float]:
        """Extract price from text string."""
        if not text:
            return None
        
        # Remove currency symbols and extract number
        match = re.search(r'[\d,]+\.?\d*', text.replace(',', ''))
        if match:
            try:
                return float(match.group())
            except ValueError:
                return None
        return None
    
    def extract_speed(self, text: str) -> Optional[float]:
        """Extract speed value from text string."""
        if not text:
            return None
        
        # Handle Gbps conversion
        if 'gb' in text.lower():
            match = re.search(r'([\d.]+)', text)
            if match:
                return float(match.group(1)) * 1000
        
        # Handle Mbps
        match = re.search(r'([\d.]+)', text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None
    
    def extract_contract_length(self, text: str) -> Optional[int]:
        """Extract contract length in months from text."""
        if not text:
            return None
        
        match = re.search(r'(\d+)', text)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        return None
    
    @abstractmethod
    async def extract_deals(self) -> List[Dict[str, Any]]:
        """
        Extract all deals from the current page.
        Must be implemented by each provider scraper.
        
        Returns:
            List of dictionaries containing deal information
        """
        pass
    
    async def scrape(
        self,
        postcode: str,
        address: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Main scraping workflow.
        
        Args:
            postcode: UK postcode to search
            address: Specific address to select (optional)
            
        Returns:
            List of broadband deals
        """
        try:
            # Initialize browser
            await self.initialize_browser()
            
            # Navigate to page
            await self.navigate_to_page()
            
            # Handle cookies
            await self.handle_cookies()
            
            # Enter postcode
            if not await self.enter_postcode(postcode):
                logger.error(f"{self.provider_name.upper()}: Failed to enter postcode")
                return []
            
            # Select address
            if not await self.select_address(address):
                logger.error(f"{self.provider_name.upper()}: Failed to select address")
                return []
            
            # Extract deals (provider-specific implementation)
            deals = await self.extract_deals()
            
            # Add metadata to all deals
            for deal in deals:
                deal["provider"] = self.provider_config.get("name", self.provider_name)
                deal["postcode"] = postcode
                deal["address"] = address
            
            logger.info(f"{self.provider_name.upper()}: Extracted {len(deals)} deals")
            return deals
            
        except Exception as e:
            logger.error(f"{self.provider_name.upper()}: Scraping failed: {str(e)}", exc_info=True)
            return []
