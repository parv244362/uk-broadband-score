"""Scraper modules for different broadband providers."""

from src.scrapers.base_scraper import BaseScraper
from src.scrapers.sky_scraper import SkyScraper
from src.scrapers.bt_scraper import BTScraper
from src.scrapers.ee_scraper import EEScraper
from src.scrapers.hyperoptic_scraper import HyperopticScraper
from src.scrapers.virgin_scraper import VirginMediaScraper
from src.scrapers.vodafone_scraper import VodafoneScraper

__all__ = [
    "BaseScraper",
    "SkyScraper",
    "BTScraper",
    "EEScraper",
    "HyperopticScraper",
    "VirginMediaScraper",
    "VodafoneScraper",
]
