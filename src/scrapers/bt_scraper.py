"""BT Broadband scraper implementation with lazy loading support."""

import re
import os
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse  # Add this import
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from src.scrapers.base_scraper import BaseScraper
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class BTScraper(BaseScraper):
    """
    Scraper for BT Broadband.
    
    Handles:
    - Lazy-loaded product cards (infinite scroll)
    - Multiple contract length tabs (12 and 24 months)
    - Modal dialogs for contract switching
    - Speed guarantees and merchandising info
    - Price rise information
    - Incremental card loading with deduplication
    """
    
    @property
    def provider_name(self) -> str:
        return "bt"
    
    def _load_provider_config(self) -> dict:
        """
        Loads the configuration for the BT provider.
        First checks if it exists in provided config, then looks for a local provider.json.
        """
        for attr in ("provider_config", "config", "providers_config"):
            cfg = getattr(self, attr, None)
            if isinstance(cfg, dict):
                if "bt" in cfg and isinstance(cfg["bt"], dict):
                    return cfg["bt"]
                if "url" in cfg:
                    return cfg

        # Check for provider.json in the current directory or parent directories
        here = Path(__file__).resolve()
        for parent in [here.parent] + list(here.parents):
            candidate = parent / "provider.json"
            if candidate.exists():
                data = json.loads(candidate.read_text(encoding="utf-8"))
                bt_cfg = data.get("bt")
                if isinstance(bt_cfg, dict):
                    return bt_cfg

        return {}
    
    async def _profile_from_url(self, url: str) -> Tuple[str, dict, str, str]:
        """
        Extracts profile information like timezone, geolocation, and language preferences based on URL.
        """
        parsed_url = urlparse(url)
        domain = (parsed_url.netloc or "").lower()

        timezone_id = "Europe/London"
        geolocation = {"latitude": 51.5074, "longitude": -0.1278}
        locale = "en-GB"
        accept_language = "en-GB,en;q=0.9"

        return timezone_id, geolocation, locale, accept_language
    
    async def _ensure_page(self) -> None:
        if getattr(self, "page", None):
            return

        self._owns_playwright = True

        # Load BT-specific config
        cfg = self._load_provider_config()
        url = cfg.get("url", "https://www.bt.com/broadband")  # Default BT URL
        timeout = int(cfg.get("timeout") or 30000)

        # Await the async function here
        timezone_id, geolocation, locale, accept_language = await self._profile_from_url(url)

        # Headless mode and other configurations
        env_headless = os.getenv("BT_HEADLESS")
        headless = env_headless is not None and env_headless.strip().lower() in ("1", "true", "yes")
        slowmo = int(os.getenv("BT_SLOWMO", "0") or "0")
        proxy_server = os.getenv("BT_PROXY_SERVER")
        proxy = {"server": proxy_server} if proxy_server else None

        # Initialize Playwright and browser
        self._pw = await async_playwright().start()
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--start-maximized",
        ]

        try:
            self._browser = await self._pw.chromium.launch(
                headless=headless,
                proxy=proxy,
                slow_mo=slowmo,
                args=launch_args,
            )
        except Exception:
            self._browser = await self._pw.chromium.launch(
                headless=headless,
                proxy=proxy,
                slow_mo=slowmo,
                args=launch_args,
            )

        self._context = await self._browser.new_context(
            viewport={"width": 1366, "height": 768},
            locale=locale,
            timezone_id=timezone_id,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            permissions=["geolocation"],
            geolocation=geolocation,
            color_scheme="light",
            extra_http_headers={"Accept-Language": accept_language},
            ignore_https_errors=True,
        )

        await self._context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-GB', 'en'] });
            """
        )

        # Create a new page
        self.page = await self._context.new_page()
        self.page.set_default_timeout(timeout)



    async def _dismiss_modal_if_present(self, modal_close_selector: str):
        """Helper method to dismiss the modal if it's visible."""
        try:
            modal_count = await self.page.locator(modal_close_selector).count()
            if modal_count > 0:
                close_button = self.page.locator(modal_close_selector).first
                await close_button.scroll_into_view_if_needed()
                if await close_button.is_visible():
                    await close_button.click()
                    logger.info("Dismissed modal successfully.")
                else:
                    logger.warning("Modal close button not visible, skipping.")
        except Exception as e:
            logger.warning(f"Error while dismissing modal: {str(e)}")
    
    async def enter_postcode_and_select_address(self, postcode: str, preferred_address: Optional[str] = None) -> bool:
        """
        Enter postcode, select address, handle BT error modal at any step.
        Retries up to 5 times if BT shows error modal after postcode or address selection.
        """
        postcode_input_selector = "#sc-postcode"
        modal_close_selector = "button:has-text('Close'), [data-testid='modal-close'], button[aria-label='Close']"
        address_button_selector = "li[data-analytics-link='Choose-address'] button"
        plans_page_indicator_selector = "div.jss1356 h2:has-text('Choose your Broadband')"

        max_attempts = 5
        attempt = 0

        while attempt < max_attempts:
            attempt += 1
            logger.info(f"BT: Attempt {attempt} to enter postcode and select address")

            try:
                # -----------------------------
                # Step 1: Enter postcode
                # -----------------------------
                postcode_input = self.page.locator(postcode_input_selector).first
                await postcode_input.wait_for(state="visible", timeout=10000)
                await postcode_input.click()
                await postcode_input.fill("")  # Clear field before typing
                for char in postcode.strip():
                    await postcode_input.type(char, delay=200)
                await self.page.wait_for_timeout(4000)

                # -----------------------------
                # Check for error modal after postcode entry
                # -----------------------------
                await self._dismiss_modal_if_present(modal_close_selector)

                # -----------------------------
                # Step 2: Wait for addresses or product cards
                # -----------------------------
                try:
                    await self.page.wait_for_selector(
                        f"{address_button_selector}, [data-testid='product-card']",
                        timeout=10000  # Increased timeout for address selection/loading
                    )
                except PlaywrightTimeoutError:
                    logger.warning("BT: Address list or product cards not loaded yet, retrying...")
                    continue  # retry the whole loop if timeout happens

                # -----------------------------
                # Step 3: Select address
                # -----------------------------
                address_buttons = self.page.locator(address_button_selector)
                count = await address_buttons.count()
                if count > 0:
                    if preferred_address:
                        selected = False
                        for i in range(count):
                            btn = address_buttons.nth(i)
                            text = (await btn.inner_text()).lower()
                            if preferred_address.lower() in text:
                                await btn.click()
                                logger.info(f"BT: Selected preferred address: {text}")
                                selected = True
                                break
                        if not selected:
                            await address_buttons.first.click()
                            logger.info("BT: Preferred address not found, selected first")
                    else:
                        await address_buttons.first.click()
                        logger.info("BT: Selected first address")
                else:
                    logger.info("BT: No addresses found, retrying...")
                    continue

                await self.page.wait_for_timeout(8000)

                # -----------------------------
                # Step 4: Check for error modal after address selection
                # -----------------------------
                await self._dismiss_modal_if_present(modal_close_selector)

                # -----------------------------
                # Step 5: Wait for plan/product cards with proper timeout handling
                # -----------------------------
                try:
                    # Wait for product cards to appear after address selection
                    await self.page.wait_for_selector("[data-testid='product-card']", timeout=20000)  # wait for product cards to load
                    logger.info("BT: Product cards loaded successfully.")

                    # Now that the plan page is fully loaded, return True and continue to the next step
                    return True  # Exit the loop and return True to continue scraping

                except PlaywrightTimeoutError:
                    logger.warning("BT: Product cards did not load after address selection.")
                    continue  # retry the whole loop if timeout happens

            except Exception as e:
                logger.warning(f"BT: Attempt {attempt} failed: {e}")

            # Retry loop after a brief wait
            logger.info(f"BT: Retrying after error at attempt {attempt}")
            await self.page.wait_for_timeout(2000)

        logger.error(f"BT: Failed to enter postcode and select address after {max_attempts} attempts")
        return False



    def _card_locator(self):
        """Get locator for product cards."""
        return self.page.locator(
            "#product-list [data-testid='product-card'], "
            "[id^='product-row-'] [data-testid='product-card']"
        )
    
    async def _safe_inner_text(self, scope, selector: str, timeout: int = 400) -> Optional[str]:
        """Safely extract text from an element."""
        loc = scope.locator(selector).first
        try:
            handle = await loc.element_handle(timeout=timeout)
        except (PlaywrightTimeoutError, Exception):
            return None
        
        if not handle:
            return None
        
        try:
            txt = await handle.text_content()
            return txt.strip() if txt else None
        except Exception:
            return None
    
    async def _extract_download_speed(self, card) -> Optional[int]:
        try:
            speed_elem = card.locator(
                "[data-testid='pc-speed-and-price'] h2"
            ).first

            text = (await speed_elem.inner_text()).lower()

            # Handle ranges like "5-13Mbps"
            range_match = re.search(r"(\d+)\s*-\s*(\d+)", text)
            if range_match:
                return int(range_match.group(2))  # max speed

            # Handle single values like "15Mbps"
            single_match = re.search(r"(\d+)", text)
            if single_match:
                return int(single_match.group(1))

        except Exception:
            pass

        return None

    
    async def _extract_upload_speed(self, card) -> Optional[str]:
        """Extract upload speed from card."""
        try:
            upload_elem = card.locator("text=/upload/i").first
            upload_text = await upload_elem.inner_text()
            speed = self.extract_speed(upload_text)
            if speed:
                return f"{speed} Mbps"
        except Exception:
            pass
        return None
    
    async def _extract_speed_guarantee(self, card) -> Optional[str]:
        """Extract speed guarantee from card."""
        # Try speed estimation link first
        guarantee = await self._safe_inner_text(card, "[data-testid='pc-speedestimation-link']")
        if guarantee:
            return guarantee
        
        # Fallback to speed guarantee element
        return await self._safe_inner_text(card, "[data-testid='pc-speed-guarantee']")
    
    async def _extract_merchandising(self, card) -> List[str]:
        """Extract merchandising/promotional text."""
        try:
            texts = await card.locator("[data-testid='pc-merch-strip']").evaluate_all(
                "nodes => nodes.map(n => (n.textContent || '').trim()).filter(Boolean)"
            )
            return [t.strip() for t in texts if t.strip()]
        except Exception:
            return []
    
    async def _extract_price_rise(self, card) -> List[str]:
        """Extract price rise information."""
        rise_info = []
        selectors = [
            "[data-testid='price-rise-year1']",
            "[data-testid='price-rise-amt1']",
            "[data-testid='price-rise-year2']",
            "[data-testid='price-rise-amt2']",
        ]
        
        for sel in selectors:
            text = await self._safe_inner_text(card, sel)
            if text:
                rise_info.append(text)
        
        return rise_info
    
    async def _get_page_technology(self) -> str:
        """
        Extract broadband technology from page-level <p> (copper/fibre).
        Returns 'Copper', 'Part Fibre', 'Full Fibre', or 'Unknown'.
        """
        try:
            # Look for any <p> that mentions copper or fibre
            p_locator = self.page.locator("p:has-text('fibre'), p:has-text('copper')").first
            if await p_locator.count() == 0:
                return "Unknown"
    
            span_locator = p_locator.locator("span").first
            if await span_locator.count() == 0:
                return "Unknown"
    
            tech_text = await span_locator.inner_text()
            if tech_text:
                tech_text = tech_text.strip().lower()
                if "copper" in tech_text:
                    return "Copper"
                elif "part fibre" in tech_text:
                    return "Part Fibre"
                elif "full fibre" in tech_text or "fibre" in tech_text:
                    return "Full Fibre"
        except Exception:
            pass
        
        return "Unknown"

    
    async def _parse_card(self, card, postcode: str, contract_override: Optional[int] = None) -> Dict[str, Any]:
        """Parse a single product card."""
        deal = {"postcode": postcode}
        
        # Extract package name
        package = await self._safe_inner_text(card, "[data-testid='pc-name-details']")
        if package:
            deal["deal_name"] = package
        
        # Extract monthly price
        price_text = await self._safe_inner_text(card, "[data-testid='pc-monthly-price']")
        if price_text:
            price = self.extract_price(price_text)
            if price:
                deal["monthly_price"] = price
        
        # Extract speeds
        download_speed = await self._extract_download_speed(card)
        if download_speed is not None:
            deal["download_speed"] = download_speed
        
        upload_speed = await self._extract_upload_speed(card)
        if upload_speed:
            deal["upload_speed"] = self.extract_speed(upload_speed)
        
        # Extract speed guarantee
        guarantee = await self._extract_speed_guarantee(card)
        if guarantee:
            deal["speed_guarantee"] = guarantee
        
        # Extract upfront cost
        upfront_text = await self._safe_inner_text(card, "[data-testid='pc-pricing-upfront-pp']")
        if upfront_text:
            upfront = self.extract_price(upfront_text)
            if upfront is not None:
                deal["upfront_cost"] = upfront
        
        # Extract contract length
        if contract_override is not None:
            deal["contract_length"] = contract_override
        else:
            contract_text = await self._safe_inner_text(card, "p:has-text('contract')")
            if contract_text:
                length = self.extract_contract_length(contract_text)
                if length:
                    deal["contract_length"] = length
        
        # Combine promotional info
        promo_bits = []
        promo_bits.extend(await self._extract_price_rise(card))
        promo_bits.extend(await self._extract_merchandising(card))
        
        if promo_bits:
            deal["promotions"] = " | ".join(promo_bits)
        
        # Set defaults
        deal.setdefault("deal_name", "BT Broadband")
        deal.setdefault("contract_length", 24)
        deal.setdefault("data_allowance", "Unlimited")
        deal["url"] = self.page.url
        
        # -------------------------
        # Final normalization
        # -------------------------

        deal["provider"] = self.provider_name

        monthly_price = deal.get("monthly_price")
        contract_length = deal.get("contract_length", 24)
        download_speed = deal.get("download_speed")

        # Total contract cost
        if monthly_price is not None and contract_length:
            deal["total_contract_cost"] = round(
                monthly_price * contract_length, 2
            )

        # Defaults expected by pipeline
        deal.setdefault("data_allowance", "Unlimited")
        deal.setdefault("router_included", None)
        deal.setdefault("installation_type", "Standard")

        # Use page-level technology for all cards
        deal["technology_type"] = await self._get_page_technology()

        # URL
        deal["url"] = self.page.url

        return deal
    
    async def _nudge_scroll(self):
        """Scroll page to trigger lazy loading."""
        try:
            await self.page.mouse.wheel(0, 800)
        except Exception:
            try:
                await self.page.evaluate("() => window.scrollBy(0, window.innerHeight)")
            except Exception:
                pass
    
    async def _wait_for_cards(self, min_cards: int = 1):
        """Wait for product cards to load."""
        await self.page.wait_for_selector("[data-testid='product-card']", timeout=15000)
        
        cards = self._card_locator()
        
        # Keep scrolling until we have enough cards
        for _ in range(30):
            count = await cards.count()
            if count >= min_cards:
                return
            
            await self._nudge_scroll()
            await self.page.wait_for_timeout(250)
    
    async def _scrape_cards(
        self,
        postcode: str,
        contract_term: Optional[int] = None,
        min_cards: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Scrape all product cards with lazy loading support.
        
        BT uses infinite scroll, so we need to incrementally load and parse cards.
        """
        await self._wait_for_cards(min_cards=min_cards)
        
        deals = []
        cards = self._card_locator()
        seen_ids = set()
        index = 0
        stable_cycles = 0
        
        logger.info(f"{self.provider_name.upper()}: Starting incremental card scraping")
        
        while True:
            total = await cards.count()
            
            # If we've processed all visible cards
            if index >= total:
                stable_cycles += 1
                
                # If nothing new loaded after multiple attempts, we're done
                if stable_cycles > 2:
                    break
                
                # Try to load more
                await self._nudge_scroll()
                await self.page.wait_for_timeout(200)
                continue
            
            stable_cycles = 0
            card = cards.nth(index)
            index += 1
            
            try:
                # Deduplicate by card ID
                card_id = await card.get_attribute("id")
                if card_id:
                    normalized_id = card_id.strip().lower()
                    if normalized_id in seen_ids:
                        continue
                    seen_ids.add(normalized_id)
                
                # Ensure card is visible
                if not await card.is_visible():
                    await card.scroll_into_view_if_needed()
                    await self.page.wait_for_timeout(200)
                
                # Parse the card
                deal = await self._parse_card(card, postcode, contract_override=contract_term)
                
                # Only add deals with essential data
                if deal.get("monthly_price") and deal.get("download_speed"):
                    deals.append(deal)
                
                # Nudge scroll to load more
                await self._nudge_scroll()
            
            except Exception as e:
                logger.debug(f"{self.provider_name.upper()}: Failed to parse card {index}: {str(e)}")
                continue
        
        logger.info(f"{self.provider_name.upper()}: Scraped {len(deals)} cards")
        return deals
    
    async def _click_switch_modal(self) -> bool:
        """
        Click the confirmation in any 12-month switch modal.
        Handles buttons or spans inside buttons, with retries.
        """
        selectors = [
            "button:has-text('Switch to 12 month')",
            "span:has-text('Switch to 12 month')"
        ]
    
        for attempt in range(3):
            for sel in selectors:
                target = self.page.locator(sel).first
                try:
                    if await target.count() == 0:
                        continue
                    
                    # If it's a span, find the parent button
                    if sel.startswith("span"):
                        parent = target.locator("xpath=ancestor::button[1]").first
                        if await parent.count() == 0:
                            continue
                        target = parent
    
                    await target.scroll_into_view_if_needed()
                    await target.click()
                    await self.page.wait_for_timeout(800)
                    logger.info(f"{self.provider_name.upper()}: Clicked modal to confirm 12-month switch")
                    return True
    
                except Exception:
                    await self.page.wait_for_timeout(500)
    
            # Slight scroll and retry
            await self._nudge_scroll()
            await self.page.wait_for_timeout(500)
    
        return False
    
    
    async def _switch_to_12_month(self) -> bool:
        """
        Switch to 12-month contract tab robustly.
        Handles tabs hidden behind modals, lazy loading, or span-based tabs.
        """
        try:
            tab_selectors = [
                "button[data-testid='bb-contract-12']",
                "button:has-text('12 month')",
                "span:has-text('12 month')"
            ]
    
            tab = None
            for sel in tab_selectors:
                locator = self.page.locator(sel).first
                if await locator.count() > 0:
                    tab = locator
                    break
                
            if not tab:
                logger.warning(f"{self.provider_name.upper()}: 12-month tab not found")
                return False
    
            # If it's a span, get the parent button
            tag_name = await tab.evaluate("(el) => el.tagName")
            if tag_name.lower() == "span":
                parent = tab.locator("xpath=ancestor::button[1]").first
                if await parent.count() > 0:
                    tab = parent
    
            # Scroll into view and click
            await tab.scroll_into_view_if_needed()
            await tab.click()
            await self.page.wait_for_timeout(500)
            logger.info(f"{self.provider_name.upper()}: Clicked 12-month contract tab")
    
            # Handle modal if it appears
            await self._click_switch_modal()
    
            # Wait for 12-month cards to load (with scrolling)
            cards = self._card_locator()
            stable_cycles = 0
            for _ in range(30):
                count = await cards.count()
                # If at least 2 cards loaded, consider success
                if count >= 2:
                    break
                stable_cycles += 1
                await self._nudge_scroll()
                await self.page.wait_for_timeout(250)
                if stable_cycles > 5:
                    break
                
            logger.info(f"{self.provider_name.upper()}: Switched to 12-month contracts")
            return True
    
        except Exception as e:
            logger.warning(f"{self.provider_name.upper()}: Failed to switch to 12-month contracts: {e}")
            return False
    
        
    async def extract_deals(self) -> List[Dict[str, Any]]:
        """
        Extract deals - not used in custom scrape() implementation.
        BT requires custom navigation and lazy loading.
        """
        return []
    
    async def scrape(self, postcode: str, address: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Main scraping workflow for BT with lazy loading and contract switching.

        Args:
            postcode: UK postcode to search
            address: Specific address (optional)

        Returns:
            List of broadband deals for both 12- and 24-month contracts
        """
        try:
            # -------------------------
            # Step 1: Initialize browser and go to landing page
            # -------------------------
            await self._ensure_page()  # Ensure page is initialized
            await self.page.goto("https://www.bt.com/broadband")  # Go to the BT landing page
            logger.info(f"{self.provider_name.upper()}: On landing page")
            await self.handle_cookies()  # Handle cookies if necessary

            # -------------------------
            # Step 2: Enter postcode and select address
            # -------------------------
            success = await self.enter_postcode_and_select_address(postcode, address)
            if not success:
                logger.error("BT: Could not enter postcode and select address, aborting scrape")
                return []

            all_deals = []

            # -------------------------
            # Step 3: Scrape 24-month contracts (default)
            # -------------------------
            logger.info(f"{self.provider_name.upper()}: Scraping 24-month contracts")
            await self.page.wait_for_selector("[data-testid='product-card']", timeout=15000)
            await self.page.wait_for_timeout(500)

            deals_24 = await self._scrape_cards(postcode, contract_term=24, min_cards=4)
            all_deals.extend(deals_24)

            # -------------------------
            # Step 4: Scrape 12-month contracts (if available)
            # -------------------------
            logger.info(f"{self.provider_name.upper()}: Attempting 12-month contracts")
            switched = await self._switch_to_12_month()
            if switched:
                # Allow extra time for cards to lazy-load
                await self.page.wait_for_timeout(2000)
                deals_12 = await self._scrape_cards(postcode, contract_term=12, min_cards=6)
                all_deals.extend(deals_12)
            else:
                logger.warning(f"{self.provider_name.upper()}: Could not access 12-month contracts")

            # -------------------------
            # Step 5: Return combined deals
            # -------------------------
            if all_deals:
                logger.info(f"{self.provider_name.upper()}: Extracted {len(all_deals)} total deals")
                return all_deals

            logger.warning(f"{self.provider_name.upper()}: No deals found")
            return []

        except Exception as e:
            logger.error(f"{self.provider_name.upper()}: Scraping failed: {str(e)}", exc_info=True)
            return []
