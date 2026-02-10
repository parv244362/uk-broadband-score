"""Sky Broadband scraper - Updated for 2026 website structure."""

import os
import re
import json
from pathlib import Path
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional, Tuple

from playwright.async_api import TimeoutError as PlaywrightTimeoutError, async_playwright

from src.scrapers.base_scraper import BaseScraper
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class SkyScraper(BaseScraper):
    @property
    def provider_name(self) -> str:
        return "sky"

    # ----------------------------
    # provider.json loader
    # ----------------------------
    def _load_provider_config(self) -> dict:
        for attr in ("provider_config", "config", "providers_config"):
            cfg = getattr(self, attr, None)
            if isinstance(cfg, dict):
                if "sky" in cfg and isinstance(cfg["sky"], dict):
                    return cfg["sky"]
                if "url" in cfg:
                    return cfg

        here = Path(__file__).resolve()
        for parent in [here.parent] + list(here.parents):
            candidate = parent / "provider.json"
            if candidate.exists():
                data = json.loads(candidate.read_text(encoding="utf-8"))
                sky_cfg = data.get("sky")
                if isinstance(sky_cfg, dict):
                    return sky_cfg

        return {}

    # ----------------------------
    # Domain -> timezone + geo profile
    # ----------------------------
    def _profile_from_url(self, url: str) -> Tuple[str, dict, str, str]:
        parsed_url = urlparse(url)
        domain = (parsed_url.netloc or "").lower()

        if ".co.uk" in domain or domain.endswith(".uk"):
            timezone_id = "Europe/London"
            geolocation = {"latitude": 51.5074, "longitude": -0.1278}  # London
            locale = "en-GB"
            accept_language = "en-GB,en;q=0.9"
        elif ".com.au" in domain or domain.endswith(".au"):
            timezone_id = "Australia/Sydney"
            geolocation = {"latitude": -33.8688, "longitude": 151.2093}
            locale = "en-AU"
            accept_language = "en-AU,en;q=0.9"
        elif domain.endswith(".ca"):
            timezone_id = "America/Toronto"
            geolocation = {"latitude": 43.6532, "longitude": -79.3832}
            locale = "en-CA"
            accept_language = "en-CA,en;q=0.9"
        elif domain.endswith(".de"):
            timezone_id = "Europe/Berlin"
            geolocation = {"latitude": 52.5200, "longitude": 13.4050}
            locale = "de-DE"
            accept_language = "de-DE,de;q=0.9,en;q=0.8"
        elif domain.endswith(".fr"):
            timezone_id = "Europe/Paris"
            geolocation = {"latitude": 48.8566, "longitude": 2.3522}
            locale = "fr-FR"
            accept_language = "fr-FR,fr;q=0.9,en;q=0.8"
        else:
            timezone_id = "America/New_York"
            geolocation = {"latitude": 40.7128, "longitude": -74.0060}
            locale = "en-US"
            accept_language = "en-US,en;q=0.9"

        return timezone_id, geolocation, locale, accept_language

    # ----------------------------
    # Playwright bootstrap (file-only)
    # ----------------------------
    async def _ensure_page(self) -> None:
        if getattr(self, "page", None):
            return

        self._owns_playwright = True

        env_headless = os.getenv("SKY_HEADLESS")
        if env_headless is not None:
            headless = env_headless.strip().lower() in ("1", "true", "yes")
        else:
            headless = bool(getattr(self, "headless", True))

        cfg = self._load_provider_config()
        url = cfg.get("url")##, "https://www.sky.com/broadband")
        timeout = int(cfg.get("timeout") or 30000)

        timezone_id, geolocation, locale, accept_language = self._profile_from_url(url)

        proxy_server = os.getenv("SKY_PROXY_SERVER")  # optional; no creds required
        proxy = {"server": proxy_server} if proxy_server else None

        self._pw = await async_playwright().start()

        try:
            self._browser = await self._pw.chromium.launch(
                channel="chrome",
                headless=headless,
                proxy=proxy,
                args=["--disable-blink-features=AutomationControlled"],
            )
        except Exception:
            self._browser = await self._pw.chromium.launch(
                headless=headless,
                proxy=proxy,
                args=["--disable-blink-features=AutomationControlled"],
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

        # Small stealth tweak
        await self._context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            """
        )

        self.page = await self._context.new_page()
        self.page.set_default_timeout(timeout)

        # Compatibility if BaseScraper expects these names
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

    # ----------------------------
    # Navigation (uses provider.json)
    # ----------------------------
    async def navigate(self) -> None:
        await self._ensure_page()
        cfg = self._load_provider_config()

        url = cfg.get("url")
        if not url:
            raise RuntimeError("Sky URL missing in provider.json (sky.url)")

        timeout = int(cfg.get("timeout") or 30000)
        wait_for = cfg.get("wait_for_selector") or "body"

        resp = await self.page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        try:
            if resp:
                logger.info(f"{self.provider_name.upper()}: Navigate status={resp.status}, url={self.page.url}")
        except Exception:
            pass

        if wait_for:
            await self.page.wait_for_selector(wait_for, timeout=timeout)

    # ----------------------------
    # Cookies (robust: supports iframes + force click + JS click fallback)
    # ----------------------------
    async def handle_cookies(self) -> bool:
        try:
            cfg = self._load_provider_config()
            timeout = int(cfg.get("timeout") or 30000)

            selectors: List[str] = []

            # Include config selectors too
            if isinstance(cfg.get("cookie_selectors"), list):
                selectors.extend(cfg["cookie_selectors"])

            # Prefer ACCEPT first, then reject, then generic fallbacks
            selectors = [
                "#onetrust-accept-btn-handler",
                "button#onetrust-accept-btn-handler",
                "button:has-text('Accept all')",
                "button:has-text('Accept All')",
                "button:has-text('Accept')",
                "button[data-test*='accept' i]",
                "button[aria-label*='accept' i]",

                "#onetrust-reject-all-handler",
                "button#onetrust-reject-all-handler",
                "button:has-text('Reject all')",
                "button:has-text('Reject All')",
                "button:has-text('Reject')",
                "button[data-test*='reject' i]",
                "button[aria-label*='reject' i]",

                ".cookie-banner button",
                ".ot-sdk-container button",
            ] + selectors

            async def click_selector(ctx, sel: str) -> bool:
                try:
                    loc = ctx.locator(sel).first
                    if await loc.count() == 0:
                        return False

                    # Wait briefly for it to become visible; if not, still try (some banners report hidden)
                    try:
                        await loc.wait_for(state="visible", timeout=3500)
                    except Exception:
                        pass

                    try:
                        await loc.scroll_into_view_if_needed()
                    except Exception:
                        pass

                    # Try normal click
                    try:
                        await loc.click(timeout=4000)
                    except Exception:
                        # Try forced click
                        try:
                            await loc.click(timeout=4000, force=True)
                        except Exception:
                            # JS click fallback
                            try:
                                await ctx.eval_on_selector(sel, "el => el.click()")
                            except Exception:
                                return False

                    await self.page.wait_for_timeout(600)

                    # If OneTrust container is gone, we are good
                    try:
                        if await self.page.locator("#onetrust-banner-sdk").count() > 0:
                            # banner still present; not a hard fail, but likely click didn't take
                            pass
                    except Exception:
                        pass

                    logger.info(f"{self.provider_name.upper()}: Cookies handled ({sel})")
                    return True
                except Exception:
                    return False

            # Poll up to 12s because cookie banner can appear late
            import time
            deadline = time.monotonic() + 12.0

            while time.monotonic() < deadline:
                # Try on main page
                for sel in selectors:
                    if await click_selector(self.page, sel):
                        return True

                # Try in iframes (OneTrust often uses iframe)
                for frame in self.page.frames:
                    for sel in selectors:
                        if await click_selector(frame, sel):
                            return True

                await self.page.wait_for_timeout(300)

            logger.info(f"{self.provider_name.upper()}: No cookie banner found/clicked")
            return False

        except Exception as e:
            logger.debug(f"{self.provider_name.upper()}: Cookie handling error: {e}")
            return False

    # Placeholder to satisfy abstract base (Sky overrides scrape)
    async def extract_deals(self) -> List[Dict[str, Any]]:
        return []

    # ----------------------------
    # Scrape
    # ----------------------------
    async def scrape(self, postcode: str, address: Optional[str] = None) -> List[Dict[str, Any]]:
        deals: List[Dict[str, Any]] = []

        try:
            await self.navigate()

            # Handle cookies BEFORE waiting for specific content
            await self.handle_cookies()

            cfg = self._load_provider_config()
            timeout = int(cfg.get("timeout") or 30000)

            # Sky layout changes often; don't depend on one text
            candidate_selectors = [
                cfg.get("deal_container_selector"),
                "text=/Full\\s*Fibre/i",
                "text=/Gigafast/i",
                "text=/Broadband/i",
                "main",
                "body",
            ]

            for sel in [s for s in candidate_selectors if s]:
                try:
                    await self.page.wait_for_selector(sel, timeout=min(20000, timeout))
                    break
                except PlaywrightTimeoutError:
                    continue

            await self.page.wait_for_timeout(1500)

            logger.info(f"{self.provider_name.upper()}: Page loaded, extracting deals")
            deals = await self._extract_deals_from_page()
            logger.info(f"{self.provider_name.upper()}: Found {len(deals)} deals")

        except Exception as e:
            logger.error(f"{self.provider_name.upper()}: Scraping failed: {e}")

        return deals

    # ----------------------------
    # Extraction (regex over text+html, supports £ and &pound;)
    # ----------------------------
    async def _extract_deals_from_page(self) -> List[Dict[str, Any]]:
        deals: List[Dict[str, Any]] = []

        try:
            await self.page.wait_for_timeout(800)

            body_text = await self.page.inner_text("body")
            html = await self.page.content()
            blob = (body_text or "") + "\n" + (html or "")

            price_pat = r"(?:£|&pound;)\s*([0-9]+(?:\.[0-9]+)?)\s*(?:/|per\s*)?(?:month|mo|pm|a\s*month)"

            packages = [
                {"name": "Full Fibre 100", "speed": 100, "pattern": rf"Full\s*Fibre\s*100.*?{price_pat}"},
                {"name": "Full Fibre 300", "speed": 300, "pattern": rf"Full\s*Fibre\s*300.*?{price_pat}"},
                {"name": "Full Fibre Gigafast", "speed": 900, "pattern": rf"Full\s*Fibre\s*Gigafast(?!\+).*?{price_pat}"},
                {"name": "Full Fibre Gigafast+", "speed": 5000, "pattern": rf"Full\s*Fibre\s*Gigafast\+.*?{price_pat}"},
            ]
            cfg = self._load_provider_config()
            for pkg in packages:
                m = re.search(pkg["pattern"], blob, re.DOTALL | re.IGNORECASE)
                if m:
                    price = float(m.group(1))
                    deals.append({
                        "deal_name": pkg["name"],
                        "provider": "Sky",
                        "monthly_price": price,
                        "upfront_cost": 0.0,
                        "download_speed": pkg["speed"],
                        "upload_speed": None,
                        "contract_length": 24,
                        "data_allowance": "Unlimited",
                        "promotional_text": "No upfront fees",
                        "url": cfg.get("url"),
                        "total_contract_cost": price * 24,
                        "installation_type": "Standard",
                        "technology_type": "FTTC" if pkg["speed"] < 100 else "FTTP",
                    })

        except Exception as e:
            logger.error(f"{self.provider_name.upper()}: Error extracting deals: {e}")

        return deals
