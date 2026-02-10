# UK Broadband Price Comparison Tool

A Python-based web scraping tool that compares broadband deals from major UK ISPs using Playwright automation.

## Features

- 🔍 Postcode-based broadband deal lookup
- 🏢 Multi-provider support (Sky, BT, EE, Hyperoptic, Virgin Media, Vodafone)
- 🤖 Automated cookie consent handling
- 📊 Comprehensive data extraction
- 💾 Export to CSV, Excel, and JSON
- 🔄 Concurrent provider scraping
- 📝 Detailed logging and error handling

## Providers Supported

- Sky Broadband
- BT Broadband
- EE Broadband
- Hyperoptic
- Virgin Media
- Vodafone Broadband

## Prerequisites

- Python 3.9 or higher
- Stable internet connection
- Minimum 4GB RAM (8GB recommended)

## Installation

1. Clone the repository:
```bash
cd bb-price-compare
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install Playwright browsers:
```bash
playwright install chromium
```

## Usage

### Basic Usage

Run the tool with a postcode:

```bash
python src/main.py --postcode "SW1A 1AA"
```

### Advanced Options

```bash
# Scrape specific providers
python src/main.py --postcode "SW1A 1AA" --providers sky bt ee

# Specify output format
python src/main.py --postcode "SW1A 1AA" --format excel

# Run with debug logging
python src/main.py --postcode "SW1A 1AA" --log-level debug

# Export to specific directory
python src/main.py --postcode "SW1A 1AA" --output ./my-results
```

## Output

Results are saved in the `output/` directory with the following naming convention:
- `broadband_comparison_YYYYMMDD_HHMMSS.csv`
- `broadband_comparison_YYYYMMDD_HHMMSS.xlsx`
- `broadband_comparison_YYYYMMDD_HHMMSS.json`

## Data Extracted

For each broadband deal, the tool extracts:

- **Pricing**: Monthly price, upfront costs, contract length, total cost
- **Speeds**: Download/upload speeds, technology type
- **Service**: Data allowance, router included, installation type
- **Metadata**: Provider, deal name, availability, timestamp

## Project Structure

```
bb-price-compare/
├── config/              # Configuration files
├── src/                 # Source code
│   ├── scrapers/        # Provider-specific scrapers
│   ├── utils/           # Utility functions
│   └── models/          # Data models
├── tests/               # Test files
├── output/              # Generated reports
└── logs/                # Application logs
```

## Configuration

Edit `config/providers.json` to update provider configurations:
- URLs
- CSS selectors
- Navigation patterns
- Extraction mappings

## Development

### Running Tests

```bash
pytest tests/
```

### Adding a New Provider

1. Create a new scraper class in `src/scrapers/`
2. Inherit from `BaseScraper`
3. Implement required methods
4. Add configuration to `config/providers.json`
5. Update `config/selectors.json`

## Troubleshooting

### Common Issues

**Browser fails to launch:**
```bash
playwright install chromium --force
```

**Selector not found:**
- Check `config/selectors.json` for updated selectors
- Provider websites may have changed - update configuration

**Timeout errors:**
- Increase timeout in `config/settings.json`
- Check internet connection stability

## Legal and Ethical Considerations

This tool is designed for:
- Personal price comparison
- Research purposes
- Educational use

**Important:**
- Implements respectful rate limiting
- Honors robots.txt directives
- Does not store personal information
- Review provider Terms of Service before use

## Maintenance

The tool requires regular maintenance due to provider website changes:
- **Weekly**: Monitor for major website changes
- **Monthly**: Update selectors if needed
- **Quarterly**: Update dependencies

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request with tests

## License

This project is for educational and personal use only.

## Support

For issues and questions, please refer to the PROJECT_REQUIREMENTS.md document.

## Changelog

### Version 1.0.0 (2026-02-03)
- Initial release
- Support for 6 major UK ISPs
- CSV, Excel, and JSON export
- Automated cookie handling
- Concurrent scraping support
