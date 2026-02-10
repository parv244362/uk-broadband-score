"""Tests for scraper modules."""

import pytest
from src.scrapers.base_scraper import BaseScraper


class TestBaseScraper:
    """Test cases for BaseScraper class."""
    
    def test_extract_price(self):
        """Test price extraction from text."""
        # Create a mock scraper instance
        class MockScraper(BaseScraper):
            @property
            def provider_name(self):
                return "test"
            
            async def extract_deals(self):
                return []
        
        scraper = MockScraper(headless=True)
        
        assert scraper.extract_price("£25.99") == 25.99
        assert scraper.extract_price("£50") == 50.0
        assert scraper.extract_price("From £30.00 per month") == 30.0
        assert scraper.extract_price("£1,234.56") == 1234.56
        assert scraper.extract_price(None) is None
    
    def test_extract_speed(self):
        """Test speed extraction from text."""
        class MockScraper(BaseScraper):
            @property
            def provider_name(self):
                return "test"
            
            async def extract_deals(self):
                return []
        
        scraper = MockScraper(headless=True)
        
        assert scraper.extract_speed("100 Mbps") == 100.0
        assert scraper.extract_speed("1 Gbps") == 1000.0
        assert scraper.extract_speed("1.5 Gb") == 1500.0
        assert scraper.extract_speed("Average 67Mb") == 67.0
        assert scraper.extract_speed(None) is None
    
    def test_extract_contract_length(self):
        """Test contract length extraction from text."""
        class MockScraper(BaseScraper):
            @property
            def provider_name(self):
                return "test"
            
            async def extract_deals(self):
                return []
        
        scraper = MockScraper(headless=True)
        
        assert scraper.extract_contract_length("18 months") == 18
        assert scraper.extract_contract_length("24 month contract") == 24
        assert scraper.extract_contract_length("12 mth") == 12
        assert scraper.extract_contract_length(None) is None


@pytest.mark.asyncio
class TestScraperIntegration:
    """Integration tests for scrapers (requires internet connection)."""
    
    # These tests should be run manually as they require actual websites
    # and may be fragile due to website changes
    
    @pytest.mark.skip(reason="Requires actual website access")
    async def test_sky_scraper(self):
        """Test Sky scraper end-to-end."""
        from src.scrapers.sky_scraper import SkyScraper
        
        scraper = SkyScraper(headless=True)
        results = await scraper.scrape(postcode="SW1A 1AA")
        
        assert isinstance(results, list)
        if results:
            assert "provider" in results[0]
            assert "monthly_price" in results[0]
    
    @pytest.mark.skip(reason="Requires actual website access")
    async def test_bt_scraper(self):
        """Test BT scraper end-to-end."""
        from src.scrapers.bt_scraper import BTScraper
        
        scraper = BTScraper(headless=True)
        results = await scraper.scrape(postcode="SW1A 1AA")
        
        assert isinstance(results, list)
