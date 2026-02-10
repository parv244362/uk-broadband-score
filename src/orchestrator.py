"""Orchestrator for managing scraping operations across multiple providers."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.scrapers.sky_scraper import SkyScraper
from src.scrapers.bt_scraper import BTScraper
from src.scrapers.ee_scraper import EEScraper
from src.scrapers.hyperoptic_scraper import HyperopticScraper
from src.scrapers.virgin_scraper import VirginMediaScraper
from src.scrapers.vodafone_scraper import VodafoneScraper
from src.utils.data_processor import DataProcessor
from src.utils.exporter import Exporter
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class Orchestrator:
    """Manages the execution of multiple scrapers and data export."""
    
    SCRAPER_CLASSES = {
        "sky": SkyScraper,
        "bt": BTScraper,
        "ee": EEScraper,
        "hyperoptic": HyperopticScraper,
        "virgin_media": VirginMediaScraper,
        "vodafone": VodafoneScraper,
    }
    
    def __init__(
        self,
        postcode: str,
        providers: List[str] = None,
        address: Optional[str] = None,
        output_format: str = "csv",
        output_dir: str = "output",
        headless: bool = True,
        concurrent: bool = False
    ):
        """
        Initialize the orchestrator.
        
        Args:
            postcode: UK postcode to search
            providers: List of provider names to scrape (or ["all"])
            address: Specific address to select (optional)
            output_format: Export format (csv, excel, json, all)
            output_dir: Directory for output files
            headless: Run browsers in headless mode
            concurrent: Run scrapers concurrently
        """
        self.postcode = postcode.upper().strip()
        self.address = address
        self.output_format = output_format
        self.output_dir = Path(output_dir)
        self.headless = headless
        self.concurrent = concurrent
        
        # Determine which providers to use
        if providers is None or "all" in providers:
            self.providers = list(self.SCRAPER_CLASSES.keys())
        else:
            self.providers = [p for p in providers if p in self.SCRAPER_CLASSES]
        
        logger.info(f"Orchestrator initialized for {len(self.providers)} provider(s)")
    
    async def run(self) -> List[Dict[str, Any]]:
        """
        Execute scraping for all configured providers.
        
        Returns:
            List of broadband deals from all providers
        """
        all_results = []
        
        try:
            if self.concurrent:
                logger.info("Running scrapers concurrently...")
                all_results = await self._run_concurrent()
            else:
                logger.info("Running scrapers sequentially...")
                all_results = await self._run_sequential()
            
            # Process and export results
            if all_results:
                processed_results = DataProcessor.process_results(all_results)
                await self._export_results(processed_results)
            
            return all_results
            
        except Exception as e:
            logger.error(f"Error in orchestration: {str(e)}", exc_info=True)
            return all_results
    
    async def _run_sequential(self) -> List[Dict[str, Any]]:
        """Run scrapers one after another."""
        all_results = []
        
        for provider_name in self.providers:
            try:
                logger.info(f"Starting {provider_name.upper()} scraper...")
                results = await self._run_scraper(provider_name)
                
                if results:
                    all_results.extend(results)
                    logger.info(f"✓ {provider_name.upper()}: {len(results)} deals found")
                else:
                    logger.warning(f"✗ {provider_name.upper()}: No deals found")
                
                # Rate limiting between providers
                await asyncio.sleep(3)
                
            except Exception as e:
                logger.error(f"✗ {provider_name.upper()} failed: {str(e)}")
                continue
        
        return all_results
    
    async def _run_concurrent(self) -> List[Dict[str, Any]]:
        """Run scrapers concurrently."""
        tasks = [
            self._run_scraper(provider_name)
            for provider_name in self.providers
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_results = []
        for provider_name, result in zip(self.providers, results):
            if isinstance(result, Exception):
                logger.error(f"✗ {provider_name.upper()} failed: {str(result)}")
            elif result:
                all_results.extend(result)
                logger.info(f"✓ {provider_name.upper()}: {len(result)} deals found")
            else:
                logger.warning(f"✗ {provider_name.upper()}: No deals found")
        
        return all_results
    
    async def _run_scraper(self, provider_name: str) -> List[Dict[str, Any]]:
        """
        Run a single scraper.
        
        Args:
            provider_name: Name of the provider to scrape
            
        Returns:
            List of deals from the provider
        """
        scraper_class = self.SCRAPER_CLASSES.get(provider_name)
        if not scraper_class:
            logger.error(f"Unknown provider: {provider_name}")
            return []
        
        scraper = scraper_class(headless=self.headless)
        
        try:
            results = await scraper.scrape(
                postcode=self.postcode,
                address=self.address
            )
            return results
        except Exception as e:
            logger.error(f"Error scraping {provider_name}: {str(e)}", exc_info=True)
            return []
        finally:
            await scraper.close()
    
    async def _export_results(self, results: List[Dict[str, Any]]) -> None:
        """
        Export results to specified format(s).
        
        Args:
            results: Processed results to export
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"broadband_comparison_{timestamp}"
        
        exporter = Exporter(output_dir=self.output_dir)
        
        formats = ["csv", "excel", "json"] if self.output_format == "all" else [self.output_format]
        
        for fmt in formats:
            try:
                filepath = exporter.export(
                    data=results,
                    format=fmt,
                    filename=base_filename
                )
                logger.info(f"Exported to {fmt.upper()}: {filepath}")
            except Exception as e:
                logger.error(f"Failed to export {fmt.upper()}: {str(e)}")
