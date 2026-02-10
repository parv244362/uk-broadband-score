"""Tests for data processor module."""

import pytest
from src.utils.data_processor import DataProcessor


class TestDataProcessor:
    """Test cases for DataProcessor class."""
    
    def test_validate_postcode_valid(self):
        """Test valid UK postcodes."""
        valid_postcodes = [
            "SW1A 1AA",
            "M1 1AE",
            "B33 8TH",
            "CR2 6XH",
            "DN55 1PT",
        ]
        
        for postcode in valid_postcodes:
            assert DataProcessor.validate_postcode(postcode) is True
    
    def test_validate_postcode_invalid(self):
        """Test invalid postcodes."""
        invalid_postcodes = [
            "INVALID",
            "12345",
            "A1",
            "",
        ]
        
        for postcode in invalid_postcodes:
            assert DataProcessor.validate_postcode(postcode) is False
    
    def test_clean_price(self):
        """Test price cleaning."""
        assert DataProcessor.clean_price("£25.99") == 25.99
        assert DataProcessor.clean_price("$50") == 50.0
        assert DataProcessor.clean_price("30") == 30.0
        assert DataProcessor.clean_price("£1,234.56") == 1234.56
        assert DataProcessor.clean_price(None) is None
        assert DataProcessor.clean_price("invalid") is None
    
    def test_clean_speed(self):
        """Test speed cleaning."""
        assert DataProcessor.clean_speed("100 Mbps") == 100.0
        assert DataProcessor.clean_speed("1 Gbps") == 1000.0
        assert DataProcessor.clean_speed("500") == 500.0
        assert DataProcessor.clean_speed("1.5 Gb") == 1500.0
        assert DataProcessor.clean_speed(None) is None
    
    def test_clean_contract_length(self):
        """Test contract length cleaning."""
        assert DataProcessor.clean_contract_length("18 months") == 18
        assert DataProcessor.clean_contract_length("2 years") == 24
        assert DataProcessor.clean_contract_length("12") == 12
        assert DataProcessor.clean_contract_length(24) == 24
        assert DataProcessor.clean_contract_length(None) is None
    
    def test_validate_deal_valid(self):
        """Test valid deal validation."""
        valid_deal = {
            "provider": "Sky",
            "monthly_price": 25.99,
            "download_speed": 67.0,
            "contract_length": 18
        }
        assert DataProcessor.validate_deal(valid_deal) is True
    
    def test_validate_deal_invalid(self):
        """Test invalid deal validation."""
        # Missing required field
        invalid_deal1 = {
            "provider": "Sky",
            "download_speed": 67.0
        }
        assert DataProcessor.validate_deal(invalid_deal1) is False
        
        # Invalid price
        invalid_deal2 = {
            "provider": "Sky",
            "monthly_price": -10.0,
            "download_speed": 67.0
        }
        assert DataProcessor.validate_deal(invalid_deal2) is False
    
    def test_normalize_deal(self):
        """Test deal normalization."""
        raw_deal = {
            "provider": "BT",
            "deal_name": "Fiber 100",
            "monthly_price": "£30.99",
            "upfront_cost": "£9.99",
            "download_speed": "100 Mbps",
            "contract_length": "18 months"
        }
        
        normalized = DataProcessor.normalize_deal(raw_deal)
        
        assert normalized["monthly_price"] == 30.99
        assert normalized["upfront_cost"] == 9.99
        assert normalized["download_speed"] == 100.0
        assert normalized["contract_length"] == 18
        assert "extraction_timestamp" in normalized
        assert "total_contract_cost" in normalized
    
    def test_sort_deals(self):
        """Test deal sorting."""
        deals = [
            {"provider": "Sky", "monthly_price": 30.0},
            {"provider": "BT", "monthly_price": 25.0},
            {"provider": "EE", "monthly_price": 35.0},
        ]
        
        sorted_deals = DataProcessor.sort_deals(deals, sort_by="monthly_price")
        
        assert sorted_deals[0]["monthly_price"] == 25.0
        assert sorted_deals[-1]["monthly_price"] == 35.0
