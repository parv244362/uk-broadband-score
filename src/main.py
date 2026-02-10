"""Main entry point for the UK Broadband Price Comparison Tool."""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import List, Optional

from src.orchestrator import Orchestrator
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="UK Broadband Price Comparison Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --postcode "SW1A 1AA"
  %(prog)s --postcode "SW1A 1AA" --providers sky bt ee
  %(prog)s --postcode "SW1A 1AA" --format excel
  %(prog)s --postcode "SW1A 1AA" --output ./results --log-level debug
        """
    )
    
    parser.add_argument(
        "--postcode",
        type=str,
        required=True,
        help="UK postcode to search for broadband deals"
    )
    
    parser.add_argument(
        "--providers",
        type=str,
        nargs="+",
        choices=["sky", "bt", "ee", "hyperoptic", "virgin_media", "vodafone", "all"],
        default=["all"],
        help="Provider(s) to scrape. Default: all"
    )
    
    parser.add_argument(
        "--address",
        type=str,
        default=None,
        help="Specific address to select. If not provided, first address will be used"
    )
    
    parser.add_argument(
        "--format",
        type=str,
        choices=["csv", "excel", "json", "all"],
        default="csv",
        help="Output format. Default: csv"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default="output",
        help="Output directory for results. Default: ./output"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level. Default: INFO"
    )
    
    parser.add_argument(
        "--headless",
        type=bool,
        default=True,
        help="Run browser in headless mode. Default: True"
    )
    
    parser.add_argument(
        "--concurrent",
        action="store_true",
        help="Run scrapers concurrently"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0"
    )
    
    return parser.parse_args()


async def main() -> int:
    """Main application entry point."""
    try:
        # Parse arguments
        args = parse_arguments()
        
        # Setup logging with specified level
        logger.setLevel(args.log_level)
        
        logger.info("=" * 70)
        logger.info("UK Broadband Price Comparison Tool v1.0.0")
        logger.info("=" * 70)
        logger.info(f"Postcode: {args.postcode}")
        logger.info(f"Providers: {', '.join(args.providers)}")
        logger.info(f"Output format: {args.format}")
        logger.info(f"Output directory: {args.output}")
        logger.info("-" * 70)
        
        # Create output directory if it doesn't exist
        output_path = Path(args.output)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize orchestrator
        orchestrator = Orchestrator(
            postcode=args.postcode,
            providers=args.providers,
            address=args.address,
            output_format=args.format,
            output_dir=args.output,
            headless=args.headless,
            concurrent=args.concurrent
        )
        
        # Run scraping
        logger.info("Starting scraping process...")
        results = await orchestrator.run()
        
        # Check results
        if results:
            logger.info("-" * 70)
            logger.info(f"✓ Successfully scraped {len(results)} deals")
            logger.info(f"✓ Results saved to: {output_path.absolute()}")
            logger.info("=" * 70)
            return 0
        else:
            logger.error("No results were collected")
            return 1
            
    except KeyboardInterrupt:
        logger.warning("\n\nProcess interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        return 1


def run():
    """Run the async main function."""
    sys.exit(asyncio.run(main()))


if __name__ == "__main__":
    run()
