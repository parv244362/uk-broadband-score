"""Data export utilities for various formats."""

import csv
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

import pandas as pd

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class Exporter:
    """Handles exporting data to various formats."""
    
    def __init__(self, output_dir: str = "output"):
        """
        Initialize exporter.
        
        Args:
            output_dir: Directory for output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def export(
        self,
        data: List[Dict[str, Any]],
        format: str = "csv",
        filename: str = None
    ) -> Path:
        """
        Export data to specified format.
        
        Args:
            data: List of deal dictionaries to export
            format: Export format (csv, excel, json)
            filename: Base filename (without extension)
            
        Returns:
            Path to exported file
        """
        if not filename:
            filename = f"broadband_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if format.lower() == "csv":
            return self.export_csv(data, filename)
        elif format.lower() in ["excel", "xlsx"]:
            return self.export_excel(data, filename)
        elif format.lower() == "json":
            return self.export_json(data, filename)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def export_csv(self, data: List[Dict[str, Any]], filename: str) -> Path:
        """
        Export data to CSV format.
        
        Args:
            data: List of deal dictionaries
            filename: Base filename without extension
            
        Returns:
            Path to CSV file
        """
        filepath = self.output_dir / f"{filename}.csv"
        
        if not data:
            logger.warning("No data to export to CSV")
            return filepath
        
        # Get all unique keys from all deals
        fieldnames = set()
        for deal in data:
            fieldnames.update(deal.keys())
        fieldnames = sorted(fieldnames)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        logger.info(f"Exported {len(data)} deals to CSV: {filepath}")
        return filepath
    
    def export_excel(self, data: List[Dict[str, Any]], filename: str) -> Path:
        """
        Export data to Excel format.
        
        Args:
            data: List of deal dictionaries
            filename: Base filename without extension
            
        Returns:
            Path to Excel file
        """
        filepath = self.output_dir / f"{filename}.xlsx"
        
        if not data:
            logger.warning("No data to export to Excel")
            return filepath
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Reorder columns for better readability
        priority_cols = [
            "provider", "deal_name", "monthly_price", "upfront_cost",
            "download_speed", "upload_speed", "contract_length",
            "total_contract_cost", "technology_type", "data_allowance"
        ]
        
        # Get columns in priority order, then remaining columns
        remaining_cols = [col for col in df.columns if col not in priority_cols]
        ordered_cols = [col for col in priority_cols if col in df.columns] + remaining_cols
        df = df[ordered_cols]
        
        # Export to Excel with formatting
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Broadband Deals', index=False)
            
            # Get the worksheet
            worksheet = writer.sheets['Broadband Deals']
            
            # Auto-adjust column widths
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(col)
                ) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)
        
        logger.info(f"Exported {len(data)} deals to Excel: {filepath}")
        return filepath
    
    def export_json(self, data: List[Dict[str, Any]], filename: str) -> Path:
        """
        Export data to JSON format.
        
        Args:
            data: List of deal dictionaries
            filename: Base filename without extension
            
        Returns:
            Path to JSON file
        """
        filepath = self.output_dir / f"{filename}.json"
        
        export_data = {
            "metadata": {
                "export_timestamp": datetime.now().isoformat(),
                "total_deals": len(data),
                "providers": list(set(deal.get("provider") for deal in data if deal.get("provider")))
            },
            "deals": data
        }
        
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(export_data, jsonfile, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported {len(data)} deals to JSON: {filepath}")
        return filepath
    
    def export_summary(self, data: List[Dict[str, Any]], filename: str = "summary") -> Path:
        """
        Export a summary report of the deals.
        
        Args:
            data: List of deal dictionaries
            filename: Base filename without extension
            
        Returns:
            Path to summary file
        """
        filepath = self.output_dir / f"{filename}.txt"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("BROADBAND PRICE COMPARISON SUMMARY\n")
            f.write("=" * 70 + "\n\n")
            
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Deals: {len(data)}\n\n")
            
            # Group by provider
            providers = {}
            for deal in data:
                provider = deal.get("provider", "Unknown")
                if provider not in providers:
                    providers[provider] = []
                providers[provider].append(deal)
            
            f.write(f"Providers: {len(providers)}\n")
            for provider, deals in providers.items():
                f.write(f"  - {provider}: {len(deals)} deals\n")
            
            f.write("\n" + "-" * 70 + "\n\n")
            
            # Price statistics
            prices = [deal["monthly_price"] for deal in data if "monthly_price" in deal]
            if prices:
                f.write("PRICE STATISTICS:\n")
                f.write(f"  Lowest: £{min(prices):.2f}/month\n")
                f.write(f"  Highest: £{max(prices):.2f}/month\n")
                f.write(f"  Average: £{sum(prices)/len(prices):.2f}/month\n\n")
            
            # Speed statistics
            speeds = [deal["download_speed"] for deal in data if "download_speed" in deal]
            if speeds:
                f.write("SPEED STATISTICS:\n")
                f.write(f"  Slowest: {min(speeds):.0f} Mbps\n")
                f.write(f"  Fastest: {max(speeds):.0f} Mbps\n")
                f.write(f"  Average: {sum(speeds)/len(speeds):.0f} Mbps\n\n")
            
            f.write("=" * 70 + "\n")
        
        logger.info(f"Exported summary to: {filepath}")
        return filepath
