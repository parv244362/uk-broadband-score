"""
Virgin Media Broadband scraper (Playwright)
Fix:
- Remove “Virgin Media Deal …” extras by ONLY accepting cards that have a real plan name (Mxxx / Gigx / Fibre Broadband)
- Price ONLY from "£xx.xx a month"
- Collect unique plan cards and cap to first 4 in page order
"""

import os
import re
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse

from playwright.async_api import async_playwright

from src.scrapers.base_scraper import BaseScraper
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class VirginMediaScraper(BaseScraper):
    @property
    def provider_name(self) -> str:
        return "virgin_media"

    def _load_provider_config(self) -> dict:
        for attr in ("provider_config", "config", "providers_config"):
            cfg = getattr(self, attr, None)
            if isinstance(cfg, dict):
                if "virgin_media" in cfg and isinstance(cfg["virgin_media"], dict):
                    return cfg["virgin_media"]
                if "url" in cfg:
                    return cfg

        here = Path(__file__).resolve()
        for parent in [here.parent] + list(here.parents):
            candidate = parent / "provider.json"
            if candidate.exists():
                data = json.loads(candidate.read_text(encoding="utf-8"))
                vm_cfg = data.get("virgin_media")
                if isinstance(vm_cfg, dict):
                    return vm_cfg

        return {}

    def _profile_from_url(self, url: str) -> Tuple[str, dict, str, str]:
        parsed_url = urlparse(url)
        domain = (parsed_url.netloc or "").lower()

        if ".co.uk" in domain or domain.endswith(".uk"):
            timezone_id = "Europe/London"
            geolocation = {"latitude": 51.5074, "longitude": -0.1278}
            locale = "en-GB"
            accept_language = "en-GB,en;q=0.9"
        else:
            timezone_id = "Europe/London"
            geolocation = {"latitude": 51.5074, "longitude": -0.1278}
            locale = "en-GB"
            accept_language = "en-GB,en;q=0.9"

        return timezone_id, geolocation, locale, accept_language

    async def _ensure_page(self) -> None:
        if getattr(self, "page", None):
            return

        self._owns_playwright = True

        cfg = self._load_provider_config()
        url = cfg.get("url")  # or "https://www.virginmedia.com/broadband"
        timeout = int(cfg.get("timeout") or 30000)

        timezone_id, geolocation, locale, accept_language = self._profile_from_url(url)

        env_headless = os.getenv("VM_HEADLESS")
        if env_headless is not None:
            headless = env_headless.strip().lower() in ("1", "true", "yes")
        else:
            headless = bool(getattr(self, "headless", True))

        slowmo = int(os.getenv("VM_SLOWMO", "0") or "0")
        proxy_server = os.getenv("VM_PROXY_SERVER")
        proxy = {"server": proxy_server} if proxy_server else None

        self._pw = await async_playwright().start()

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-features=LocalNetworkAccessChecks",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-infobars",
            "--start-maximized",
            "--window-size=1920,1080",
            "--window-position=0,0",
            "--disable-features=WebBluetooth",
        ]

        try:
            self._browser = await self._pw.chromium.launch(
                channel="chrome",
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
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
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
            Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
            window.chrome = window.chrome || { runtime: {} };
            """
        )

        self.page = await self._context.new_page()
        self.page.set_default_timeout(timeout)

        self.browser = self._browser
        self.context = self._context

    async def close(self) -> None:
        try:
            await super().close()
        except Exception:
            pass

        if getattr(self, "_owns_playwright", False):
            try:
                if getattr(self, "_context", None):
                    await self._context.close()
            except Exception:
                pass
            try:
                if getattr(self, "_browser", None):
                    await self._browser.close()
            except Exception:
                pass
            try:
                if getattr(self, "_pw", None):
                    await self._pw.stop()
            except Exception:
                pass

            self.page = None
            self._context = None
            self._browser = None
            self._pw = None

    def _step(self, msg: str) -> None:
        logger.info(f"{self.provider_name.upper()}: {msg}")

    async def handle_cookies(self) -> bool:
        try:
            cfg = self._load_provider_config()
            selectors: List[str] = []
            if isinstance(cfg.get("cookie_selectors"), list):
                selectors.extend(cfg["cookie_selectors"])

            selectors = [
                "#onetrust-accept-btn-handler",
                "button#onetrust-accept-btn-handler",
                "button:has-text('Accept all')",
                "button:has-text('Accept All')",
                "button:has-text('Accept')",
                "button[aria-label*='accept' i]",
                "#onetrust-reject-all-handler",
                "button#onetrust-reject-all-handler",
                "button:has-text('Reject all')",
                "button:has-text('Reject All')",
                "button:has-text('Reject')",
                "button[aria-label*='reject' i]",
            ] + selectors

            async def click_any(ctx) -> bool:
                for sel in selectors:
                    try:
                        loc = ctx.locator(sel).first
                        if await loc.count() == 0:
                            continue
                        try:
                            await loc.wait_for(state="visible", timeout=3500)
                        except Exception:
                            pass
                        try:
                            await loc.scroll_into_view_if_needed()
                        except Exception:
                            pass
                        try:
                            await loc.click(timeout=3500)
                        except Exception:
                            try:
                                await loc.click(timeout=3500, force=True)
                            except Exception:
                                try:
                                    await ctx.eval_on_selector(sel, "el => el.click()")
                                except Exception:
                                    continue
                        return True
                    except Exception:
                        continue
                return False

            deadline = time.monotonic() + 12.0
            while time.monotonic() < deadline:
                if await click_any(self.page):
                    await self.page.wait_for_timeout(600)
                    self._step("Cookies handled")
                    return True

                for fr in self.page.frames:
                    try:
                        if await click_any(fr):
                            await self.page.wait_for_timeout(600)
                            self._step("Cookies handled (iframe)")
                            return True
                    except Exception:
                        continue

                await self.page.wait_for_timeout(300)

            self._step("No cookie banner found/clicked")
            return False
        except Exception:
            return False

    async def enter_postcode(self, postcode: str) -> bool:
        cfg = self._load_provider_config()
        timeout = int(cfg.get("timeout") or 30000)

        postcode = (postcode or "").strip().upper()
        if not postcode:
            return False

        await self.handle_cookies()

        postcode_sel = "input[data-cy='postcode-input'], input#postcode"
        submit_sel = (
            "button[data-cy='postcode-check-availability-button'], "
            "button:has-text('Check availability'), "
            "button[type='submit']"
        )

        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=min(15000, timeout))
        except Exception:
            pass

        await self.page.wait_for_timeout(900)

        inp = self.page.locator(postcode_sel).first
        try:
            await inp.wait_for(state="attached", timeout=15000)
        except Exception:
            return False

        try:
            await inp.scroll_into_view_if_needed()
        except Exception:
            pass

        try:
            await inp.click(timeout=5000)
        except Exception:
            try:
                await inp.click(timeout=5000, force=True)
            except Exception:
                pass

        try:
            await inp.fill("")
        except Exception:
            pass
        try:
            await inp.press("Control+A")
            await inp.press("Backspace")
        except Exception:
            pass

        try:
            await inp.type(postcode, delay=35)
        except Exception:
            try:
                await self.page.keyboard.type(postcode, delay=35)
            except Exception:
                return False

        try:
            val = (await inp.input_value()).strip().upper()
        except Exception:
            val = ""
        if val != postcode:
            self._step("Postcode typed but not reflected in input")
            return False

        btn = self.page.locator(submit_sel).first
        try:
            await btn.wait_for(state="attached", timeout=10000)
            try:
                await btn.click(timeout=10000)
            except Exception:
                await btn.click(timeout=10000, force=True)
        except Exception:
            try:
                await inp.press("Enter")
            except Exception:
                return False

        self._step(f"Postcode entered: {postcode}")
        return True

    async def _click_bottom_check_availability(self) -> bool:
        try:
            btns = self.page.locator("button:has-text('Check availability')")
            n = await btns.count()
            if n == 0:
                return False
            target = btns.nth(n - 1)
            try:
                await target.scroll_into_view_if_needed()
            except Exception:
                pass
            try:
                await target.click(timeout=12000)
            except Exception:
                await target.click(timeout=12000, force=True)
            return True
        except Exception:
            return False

    async def select_first_address_and_continue(self, postcode: str) -> bool:
        postcode = (postcode or "").strip().upper()

        is_multi = False
        try:
            await self.page.wait_for_selector("text=Select address", timeout=6000)
            is_multi = True
        except Exception:
            is_multi = False

        is_single = False
        try:
            await self.page.wait_for_selector("text=We've found a match", timeout=6000)
            is_single = True
        except Exception:
            is_single = False

        if is_multi:
            err = self.page.locator("text=Please select an address").first

            async def click_clickable_ancestor(text_locator) -> bool:
                try:
                    h = await text_locator.element_handle()
                    if not h:
                        return False
                    clickable = await self.page.evaluate_handle(
                        "(el) => el.closest('button,[role=\"option\"],[tabindex=\"0\"],a,li,div') || el",
                        h,
                    )
                    try:
                        await clickable.scroll_into_view_if_needed()
                    except Exception:
                        pass
                    try:
                        await clickable.click(timeout=8000)
                    except Exception:
                        await clickable.click(timeout=8000, force=True)
                    await self.page.wait_for_timeout(350)
                    return True
                except Exception:
                    return False

            picked = False
            flat1 = self.page.locator("text=/^\\s*FLAT\\s*1\\b/i").first
            if await flat1.count() > 0:
                picked = await click_clickable_ancestor(flat1)

            if not picked:
                pc = re.escape(postcode).replace("\\ ", r"\s*")
                by_pc = self.page.locator(f"text=/{pc}/i").first
                if await by_pc.count() > 0:
                    picked = await click_clickable_ancestor(by_pc)

            if not picked:
                try:
                    await self.page.keyboard.press("ArrowDown")
                    await self.page.keyboard.press("Enter")
                    await self.page.wait_for_timeout(350)
                except Exception:
                    pass

            try:
                if await err.is_visible(timeout=800):
                    if await flat1.count() > 0:
                        await click_clickable_ancestor(flat1)
            except Exception:
                pass

            await self._click_bottom_check_availability()
            self._step("Address selected + Check availability clicked")

        elif is_single:
            clicked = await self._click_bottom_check_availability()
            if clicked:
                self._step("Single address match: Check availability clicked")
            else:
                self._step("Single address match: Check availability button not found")
        else:
            clicked = await self._click_bottom_check_availability()
            if clicked:
                self._step("Check availability clicked (fallback)")
            else:
                self._step("Address step not detected (skipped)")

        return True

    async def choose_broadband_and_lets_go(self) -> bool:
        cfg = self._load_provider_config()
        timeout = int(cfg.get("timeout") or 30000)

        await self.page.wait_for_timeout(800)

        deal_type_select = (
            "select#deal_type_filter, "
            "select[data-cy='price-filter-deal-type'], "
            "select[data-testid='form-select-field--deal_type_filter']"
        )

        try:
            await self.page.wait_for_selector(deal_type_select, timeout=min(20000, timeout))
            try:
                await self.page.select_option(deal_type_select, value="Broadband")
                await self.page.wait_for_timeout(500)
                self._step("Deal type selected: Broadband")
            except Exception:
                await self.page.eval_on_selector(
                    deal_type_select,
                    """(el) => { el.value='Broadband'; el.dispatchEvent(new Event('change', {bubbles:true})); }"""
                )
                await self.page.wait_for_timeout(500)
                self._step("Deal type selected: Broadband (JS)")
        except Exception:
            self._step("Deal type dropdown not found; continuing")

        lets_go = self.page.locator("button:has-text(\"Let's go\"), button:has-text('Lets go')").first
        start_url = self.page.url

        try:
            await lets_go.scroll_into_view_if_needed()
        except Exception:
            pass

        try:
            await lets_go.click(timeout=12000)
        except Exception:
            await lets_go.click(timeout=12000, force=True)

        try:
            await self.page.wait_for_url(lambda u: u != start_url, timeout=min(20000, timeout))
        except Exception:
            pass

        try:
            await self.page.wait_for_load_state("domcontentloaded", timeout=min(20000, timeout))
        except Exception:
            pass

        try:
            await self.page.wait_for_selector("button:has-text('Add to basket')", timeout=min(25000, timeout))
        except Exception:
            pass

        self._step("Clicked Let's go and reached plans page")
        return True

    # ----------------------------
    # Extraction
    # ----------------------------
    def _parse_monthly_price(self, text: str) -> Optional[float]:
        if not text:
            return None
        m = re.search(r"£\s*([0-9]+(?:\.[0-9]+)?)\s*(?:a\s*)?month", text, flags=re.IGNORECASE)
        return float(m.group(1)) if m else None

    def _parse_speed_mbps(self, text: str) -> Optional[int]:
        if not text:
            return None
        m = re.search(r"(\d+(?:\.\d+)?)\s*([GM])bps", text, flags=re.IGNORECASE)
        if m:
            val = float(m.group(1))
            unit = m.group(2).upper()
            return int(val * 1000) if unit == "G" else int(val)
        m2 = re.search(r"(\d{2,5})\s*Mbps", text, flags=re.IGNORECASE)
        return int(m2.group(1)) if m2 else None

    async def _extract_card_from_add_to_basket(self, btn_handle):
        try:
            card_handle = await self.page.evaluate_handle(
                """
                (btn) => {
                  function countAddToBasket(el){
                    const btns = el.querySelectorAll('button');
                    let c = 0;
                    for (const b of btns){
                      const t = (b.innerText || '').trim().toLowerCase();
                      if (t === 'add to basket') c++;
                    }
                    return c;
                  }

                  let el = btn;
                  for (let i = 0; i < 18 && el; i++) {
                    const txt = (el.innerText || '').toLowerCase();
                    const hasPlanWords = txt.includes('fibre broadband') || txt.includes('broadband');
                    const hasMonthPrice = /£\\s*\\d+(?:\\.\\d+)?\\s*(?:a\\s*)?month/i.test(el.innerText || '');
                    const oneBtn = countAddToBasket(el) === 1;
                    if (oneBtn && hasMonthPrice && hasPlanWords) return el;
                    el = el.parentElement;
                  }
                  return btn.closest('article,section,li,div') || btn.parentElement;
                }
                """,
                btn_handle,
            )
            return card_handle
        except Exception:
            return None

    async def extract_deals(self) -> List[Dict[str, Any]]:
        cfg = self._load_provider_config()
        timeout = int(cfg.get("timeout") or 30000)

        try:
            await self.page.wait_for_selector("button:has-text('Add to basket')", timeout=min(25000, timeout))
        except Exception:
            self._step("No 'Add to basket' buttons found; cannot extract deals")
            return []

        # Collect UNIQUE plan cards in DOM order (then cap to 4)
        btns = self.page.locator("button:has-text('Add to basket')")
        btn_count = await btns.count()

        unique_cards = []
        seen_uids = set()

        for i in range(min(btn_count, 50)):
            bh = await btns.nth(i).element_handle()
            if not bh:
                continue

            card_h = await self._extract_card_from_add_to_basket(bh)
            if not card_h:
                continue

            # assign a stable uid on the element to dedupe
            try:
                uid = await self.page.evaluate(
                    "(el) => el.dataset.gdaUid || (el.dataset.gdaUid = Math.random().toString(36).slice(2))",
                    card_h,
                )
            except Exception:
                continue

            if uid in seen_uids:
                continue
            seen_uids.add(uid)
            unique_cards.append(card_h)

        deals: List[Dict[str, Any]] = []
        seen_names = set()

        for card_h in unique_cards:
            if len(deals) >= 4:  # cap to 4 as requested
                break

            try:
                try:
                    card_text = await card_h.inner_text()
                except Exception:
                    card_text = (await card_h.text_content()) or ""
                card_text_norm = " ".join((card_text or "").split())

                # STRICT deal name: must be real plan name
                deal_name = None
                try:
                    h = await card_h.query_selector("h1,h2,h3")
                    if h:
                        deal_name = (await h.inner_text()).strip()
                except Exception:
                    deal_name = None

                if not deal_name:
                    mname = re.search(r"\b(M\d{2,4}|Gig\d)\b.*?\bFibre\s+Broadband\b", card_text_norm, re.IGNORECASE)
                    deal_name = mname.group(0).strip() if mname else None

                # If still no real name -> SKIP (this removes the extra "Virgin Media Deal ..." row)
                if not deal_name:
                    continue

                # dedupe by name
                if deal_name in seen_names:
                    continue
                seen_names.add(deal_name)

                pc = (getattr(self, "_current_postcode", "") or "").strip().upper()

                monthly_price = self._parse_monthly_price(card_text_norm)
                download_speed = self._parse_speed_mbps(card_text_norm)

                # must have BOTH for a valid deal card
                if monthly_price is None or download_speed is None:
                    continue

                contract_length = 24
                mcl = re.search(r"(\d{1,2})\s*month", card_text_norm, re.IGNORECASE)
                if mcl:
                    contract_length = int(mcl.group(1))

                deals.append(
                    {
                        "postcode": pc,
                        "deal_name": deal_name,
                        "provider": "Virgin Media",
                        "monthly_price": monthly_price,
                        "upfront_cost": 0.0,
                        "download_speed": download_speed,
                        "upload_speed": None,
                        "contract_length": contract_length,
                        "data_allowance": "Unlimited",
                        "url": self.page.url,
                        "technology_type": "Cable",
                        "total_contract_cost": monthly_price * contract_length,
                        "installation_type": "Standard",
                        "technology_type": "FTTC" if download_speed < 100 else "FTTP"
                    }
                )
            except Exception:
                continue

        self._step(f"Extracted deals: {len(deals)}")
        return deals

    async def scrape(self, postcode: str, address: Optional[str] = None) -> List[Dict[str, Any]]:
        await self._ensure_page()
        cfg = self._load_provider_config()

        url = cfg.get("url")  # or "https://www.virginmedia.com/broadband"
        timeout = int(cfg.get("timeout") or 30000)

        resp = await self.page.goto(
            url,
            wait_until="load",
            timeout=timeout,
            referer="https://www.google.com/",
        )

        status = resp.status if resp else None
        self._step(f"Navigate status={status}, url={self.page.url}")

        if status == 403:
            self._step("403 Forbidden (WAF/bot protection)")
            return []

        await self.handle_cookies()

        pc = (postcode or "").strip().upper()

        # ✅ FIX: store postcode on instance so extract_deals() can use it
        self._current_postcode = pc

        ok = await self.enter_postcode(pc)
        if not ok:
            self._step("Failed to enter postcode")
            return []

        await self.select_first_address_and_continue(pc)
        await self.choose_broadband_and_lets_go()

        return await self.extract_deals()
