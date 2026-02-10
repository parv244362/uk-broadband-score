"""Data processing and validation utilities."""

import re
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class DataProcessor:
    """Processes and validates scraped broadband data."""
    
    @staticmethod
    def validate_postcode(postcode: str) -> bool:
        """
        Validate UK postcode format.
        
        Args:
            postcode: Postcode string to validate
            
        Returns:
            True if valid, False otherwise
        """
        # UK postcode regex pattern
        pattern = r'^[A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2}$'
        return bool(re.match(pattern, postcode.upper().strip()))
    
    @staticmethod
    def clean_price(value: Any) -> Optional[float]:
        """
        Clean and convert price value to float.
        
        Args:
            value: Price value to clean
            
        Returns:
            Float value or None if invalid
        """
        if value is None:
            return None
        
        if isinstance(value, (int, float)):
            return float(value)
        
        # Remove currency symbols and text
        cleaned = re.sub(r'[£$€,]', '', str(value))
        cleaned = re.sub(r'[^\d.]', '', cleaned)
        
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def clean_speed(value: Any) -> Optional[float]:
        """
        Clean and convert speed value to Mbps.
        
        Args:
            value: Speed value to clean
            
        Returns:
            Float value in Mbps or None if invalid
        """
        if value is None:
            return None
        
        if isinstance(value, (int, float)):
            return float(value)
        
        text = str(value).lower()
        
        # Convert Gbps to Mbps
        if 'gb' in text or 'gig' in text:
            match = re.search(r'(\d+\.?\d*)', text)
            if match:
                return float(match.group(1)) * 1000
        
        # Extract Mbps
        match = re.search(r'(\d+\.?\d*)', text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        
        return None
    
    @staticmethod
    def clean_contract_length(value: Any) -> Optional[int]:
        """
        Clean and convert contract length to months.
        
        Args:
            value: Contract length value to clean
            
        Returns:
            Integer value in months or None if invalid
        """
        if value is None:
            return None
        
        if isinstance(value, int):
            return value
        
        text = str(value).lower()
        
        # Extract number
        match = re.search(r'(\d+)', text)
        if match:
            months = int(match.group(1))
            
            # Convert years to months if specified
            if 'year' in text:
                months *= 12
            
            return months
        
        return None
    
    @staticmethod
    def validate_deal(deal: Dict[str, Any]) -> bool:
        """
        Validate that a deal has required fields.
        
        Args:
            deal: Deal dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = ["provider", "monthly_price", "download_speed"]
        
        for field in required_fields:
            if field not in deal or deal[field] is None:
                logger.warning(f"Deal missing required field: {field}")
                return False
        
        # Validate price ranges
        if deal["monthly_price"] <= 0 or deal["monthly_price"] > 200:
            logger.warning(f"Invalid monthly price: {deal['monthly_price']}")
            return False
        
        # Validate speed ranges
        if deal["download_speed"] < 10 or deal["download_speed"] > 10000:
            logger.warning(f"Invalid download speed: {deal['download_speed']}")
            return False
        
        return True
    
    @staticmethod
    def normalize_deal(deal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize deal data to consistent format.
        
        Args:
            deal: Raw deal dictionary
            
        Returns:
            Normalized deal dictionary
        """
        normalized = deal.copy()
        
        # Clean numeric fields
        if "monthly_price" in normalized:
            normalized["monthly_price"] = DataProcessor.clean_price(normalized["monthly_price"])
        
        if "upfront_cost" in normalized:
            normalized["upfront_cost"] = DataProcessor.clean_price(normalized["upfront_cost"]) or 0.0
        
        if "download_speed" in normalized:
            normalized["download_speed"] = DataProcessor.clean_speed(normalized["download_speed"])
        
        if "upload_speed" in normalized:
            normalized["upload_speed"] = DataProcessor.clean_speed(normalized["upload_speed"])
        
        if "contract_length" in normalized:
            normalized["contract_length"] = DataProcessor.clean_contract_length(normalized["contract_length"])
        
        # Calculate total cost if not present
        if "total_contract_cost" not in normalized and normalized.get("monthly_price") and normalized.get("contract_length"):
            normalized["total_contract_cost"] = (
                normalized.get("upfront_cost", 0) +
                (normalized["monthly_price"] * normalized["contract_length"])
            )
        
        # Add extraction timestamp if not present
        if "extraction_timestamp" not in normalized:
            normalized["extraction_timestamp"] = datetime.now().isoformat()
        
        # Set defaults
        normalized.setdefault("data_allowance", "Unlimited")
        normalized.setdefault("router_included", None)
        normalized.setdefault("installation_type", "Standard")
        
        return normalized
    
    @staticmethod
    def process_results(deals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process and validate all deals.
        
        Args:
            deals: List of raw deal dictionaries
            
        Returns:
            List of validated and normalized deals
        """
        processed = []
        
        for deal in deals:
            try:
                # Normalize the deal
                normalized = DataProcessor.normalize_deal(deal)
                
                # Validate the deal
                if DataProcessor.validate_deal(normalized):
                    processed.append(normalized)
                else:
                    logger.warning(f"Invalid deal skipped: {deal.get('deal_name', 'Unknown')}")
            except Exception as e:
                logger.error(f"Error processing deal: {str(e)}")
                continue
        
        logger.info(f"Processed {len(processed)}/{len(deals)} deals successfully")
        return processed
    
    @staticmethod
    def sort_deals(
        deals: List[Dict[str, Any]],
        sort_by: str = "monthly_price",
        ascending: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Sort deals by specified field.
        
        Args:
            deals: List of deal dictionaries
            sort_by: Field name to sort by
            ascending: Sort in ascending order if True
            
        Returns:
            Sorted list of deals
        """
        try:
            return sorted(
                deals,
                key=lambda x: x.get(sort_by, float('inf')),
                reverse=not ascending
            )
        except Exception as e:
            logger.error(f"Error sorting deals: {str(e)}")
            return deals
