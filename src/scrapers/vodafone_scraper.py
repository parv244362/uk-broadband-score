"""Vodafone Broadband scraper implementation."""

from typing import List, Dict, Any
from src.scrapers.base_scraper import BaseScraper
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class VodafoneScraper(BaseScraper):
    """Scraper for Vodafone Broadband."""
    
    @property
    def provider_name(self) -> str:
        return "vodafone"
    
    async def extract_deals(self) -> List[Dict[str, Any]]:
        """Extract Vodafone broadband deals from the page."""
        deals = []
        
        try:
            deal_selector = self.provider_config.get("deal_container_selector")
            await self.page.wait_for_selector(deal_selector, timeout=10000)
            
            deal_elements = await self.page.query_selector_all(deal_selector)
            logger.info(f"{self.provider_name.upper()}: Found {len(deal_elements)} deal containers")
            
            extraction_map = self.provider_config.get("extraction_map", {})
            
            for idx, deal_element in enumerate(deal_elements):
                try:
                    deal = await self._extract_single_deal(deal_element, extraction_map, idx)
                    if deal.get("monthly_price") and deal.get("download_speed"):
                        deals.append(deal)
                except Exception as e:
                    logger.warning(f"{self.provider_name.upper()}: Failed to extract deal {idx + 1}: {str(e)}")
                    continue
            
        except Exception as e:
            logger.error(f"{self.provider_name.upper()}: Failed to extract deals: {str(e)}")
        
        return deals
    
    async def _extract_single_deal(self, deal_element, extraction_map: dict, idx: int) -> Dict[str, Any]:
        """Extract data from a single deal element."""
        deal = {}
        
        if name_selector := extraction_map.get("deal_name"):
            name_elem = await deal_element.query_selector(name_selector)
            deal["deal_name"] = await name_elem.inner_text() if name_elem else f"Vodafone Deal {idx + 1}"
        
        if price_selector := extraction_map.get("monthly_price"):
            price_elem = await deal_element.query_selector(price_selector)
            if price_elem:
                price_text = await price_elem.inner_text()
                deal["monthly_price"] = self.extract_price(price_text)
        
        if upfront_selector := extraction_map.get("upfront_cost"):
            upfront_elem = await deal_element.query_selector(upfront_selector)
            if upfront_elem:
                upfront_text = await upfront_elem.inner_text()
                deal["upfront_cost"] = self.extract_price(upfront_text) or 0.0
        
        if speed_selector := extraction_map.get("download_speed"):
            speed_elem = await deal_element.query_selector(speed_selector)
            if speed_elem:
                speed_text = await speed_elem.inner_text()
                deal["download_speed"] = self.extract_speed(speed_text)
        
        if upload_selector := extraction_map.get("upload_speed"):
            upload_elem = await deal_element.query_selector(upload_selector)
            if upload_elem:
                upload_text = await upload_elem.inner_text()
                deal["upload_speed"] = self.extract_speed(upload_text)
        
        if contract_selector := extraction_map.get("contract_length"):
            contract_elem = await deal_element.query_selector(contract_selector)
            if contract_elem:
                contract_text = await contract_elem.inner_text()
                deal["contract_length"] = self.extract_contract_length(contract_text)
        
        if data_selector := extraction_map.get("data_allowance"):
            data_elem = await deal_element.query_selector(data_selector)
            deal["data_allowance"] = await data_elem.inner_text() if data_elem else "Unlimited"
        
        deal["url"] = self.page.url
        
        return deal