# UK Broadband Price Comparison Tool
## Project Requirements Document

**Version:** 1.0  
**Date:** 3 February 2026  
**Status:** Draft

---

## 1. Executive Summary

The UK Broadband Price Comparison Tool is a Python-based web scraping solution designed to automate the collection and comparison of broadband pricing information from major UK Internet Service Providers (ISPs). The tool will utilize Playwright for browser automation to extract pricing details based on user-provided postcodes, enabling transparent price comparison across multiple providers.

---

## 2. Project Objectives

### Primary Objectives
- Automate broadband price data collection from major UK ISPs
- Provide postcode-specific pricing information
- Enable standardized comparison across different providers
- Export collected data in a structured format for analysis

### Success Criteria
- Successfully scrape data from all target providers
- Handle different website structures and navigation patterns
- Process requests within reasonable timeframes (< 5 minutes per provider)
- Achieve 95%+ data accuracy
- Generate exportable reports in standard formats (CSV, Excel, JSON)

---

## 3. Scope

### In Scope
- Web scraping from the following providers:
  - Sky Broadband
  - BT Broadband
  - EE Broadband
  - Hyperoptic
  - Virgin Media
  - Vodafone Broadband
  - Additional providers as specified

- Features:
  - Postcode-based price lookup
  - Address selection from available addresses
  - Cookie consent handling
  - Form filling automation
  - Data extraction and normalization
  - Multi-format data export

### Out of Scope
- Real-time price monitoring dashboard
- User authentication system
- Historical price tracking database
- Mobile app development
- Provider signup automation
- Payment processing

---

## 4. Technical Requirements

### 4.1 Technology Stack

**Primary Technologies:**
- **Language:** Python 3.9+
- **Web Automation:** Playwright
- **Data Processing:** Pandas
- **Data Export:** openpyxl, CSV module

**Supporting Libraries:**
- asyncio (for async scraping)
- logging (for execution tracking)
- json (for configuration management)
- datetime (for timestamp management)

### 4.2 System Requirements
- Operating System: Windows 10+, macOS 10.15+, or Linux
- RAM: Minimum 4GB, Recommended 8GB
- Storage: 500MB for application and dependencies
- Internet: Stable broadband connection

---

## 5. User Workflow

### 5.1 Standard Scraping Process

The tool will execute the following steps for each provider:

```
1. Initialize Browser
   ├── Launch Playwright browser instance
   └── Set viewport and user agent

2. Visit Broadband Page
   ├── Navigate to provider's broadband deals page
   └── Wait for page load

3. Handle Cookie Consent
   ├── Detect cookie banner
   ├── Click "Reject All" or equivalent
   └── Confirm banner dismissal

4. Navigate to Postcode Input
   ├── Locate postcode entry section
   └── Prepare for data entry

5. Enter Postcode
   ├── Input user-provided postcode
   ├── Trigger search/lookup
   └── Wait for address results

6. Select Address
   ├── Parse available addresses
   ├── Select specified address (or first available)
   └── Confirm selection

7. Complete Required Forms
   ├── Fill any mandatory fields
   ├── Select default options where needed
   └── Submit/proceed to offers

8. Extract Deal Information
   ├── Identify all available deals
   ├── Extract specified metrics for each deal
   └── Store in structured format

9. Export Data
   ├── Compile all extracted data
   ├── Format according to output specification
   └── Save to file(s)
```

---

## 6. Data Extraction Requirements

### 6.1 Key Metrics to Extract

The following information must be captured for each broadband deal:

**Pricing Information:**
- Monthly price (standard and promotional)
- Upfront cost / Setup fee
- Contract length (months)
- Price after promotional period
- Total contract cost

**Service Details:**
- Download speed (Mbps)
- Upload speed (Mbps)
- Technology type (Fiber, FTTC, FTTP, Cable)
- Data allowance (unlimited/capped)
- Router included (Yes/No)

**Additional Information:**
- Provider name
- Deal/Package name
- Special offers/promotions
- Installation type (standard/premium)
- Availability date
- Phone line included (if applicable)
- TV bundles (if applicable)
- Minimum term commitment

**Metadata:**
- Extraction timestamp
- Postcode searched
- Address selected
- URL of the offer

### 6.2 Data Validation

- Verify all prices are numeric and in GBP
- Ensure speed values are in consistent units (Mbps)
- Validate contract lengths are in months
- Check for missing or null values
- Flag unusual or suspicious data points

---

## 7. Provider-Specific Implementation

### 7.1 Provider Configuration

Each provider requires a unique configuration due to different website structures:

```python
provider_config = {
    "provider_name": {
        "url": "Starting URL",
        "cookie_selector": "CSS selector for cookie reject button",
        "postcode_input_selector": "CSS selector for postcode field",
        "address_selector": "CSS selector for address dropdown/list",
        "deal_container_selector": "CSS selector for deal cards",
        "extraction_map": {
            "price": "selector for price",
            "speed": "selector for speed",
            # ... additional mappings
        }
    }
}
```

### 7.2 Navigation Patterns

Document specific navigation patterns for each provider:

**Sky Broadband:**
- URL: [To be specified]
- Cookie handling: [To be specified]
- Postcode flow: [To be specified]

**BT Broadband:**
- URL: [To be specified]
- Cookie handling: [To be specified]
- Postcode flow: [To be specified]

**EE Broadband:**
- URL: [To be specified]
- Cookie handling: [To be specified]
- Postcode flow: [To be specified]

**Hyperoptic:**
- URL: [To be specified]
- Cookie handling: [To be specified]
- Postcode flow: [To be specified]

**Virgin Media:**
- URL: [To be specified]
- Cookie handling: [To be specified]
- Postcode flow: [To be specified]

**Vodafone Broadband:**
- URL: [To be specified]
- Cookie handling: [To be specified]
- Postcode flow: [To be specified]

---

## 8. System Architecture

### 8.1 High-Level Architecture

```
┌─────────────────────────────────────────┐
│         User Interface / CLI            │
│  (Postcode input, Configuration)        │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│      Orchestration Layer                │
│  - Provider selection                   │
│  - Execution management                 │
│  - Error handling                       │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│      Scraper Modules                    │
│  - Sky Scraper                          │
│  - BT Scraper                           │
│  - EE Scraper                           │
│  - Hyperoptic Scraper                   │
│  - Virgin Media Scraper                 │
│  - Vodafone Scraper                     │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│      Playwright Browser Automation      │
│  - Page navigation                      │
│  - Element interaction                  │
│  - Data extraction                      │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│      Data Processing Layer              │
│  - Data validation                      │
│  - Normalization                        │
│  - Transformation                       │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│      Export Layer                       │
│  - CSV export                           │
│  - Excel export                         │
│  - JSON export                          │
└─────────────────────────────────────────┘
```

### 8.2 Directory Structure

```
bb-price-compare/
├── README.md
├── requirements.txt
├── setup.py
├── config/
│   ├── providers.json          # Provider configurations
│   ├── selectors.json           # CSS/XPath selectors
│   └── settings.json            # Application settings
├── src/
│   ├── __init__.py
│   ├── main.py                  # Entry point
│   ├── orchestrator.py          # Main orchestration logic
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── base_scraper.py     # Abstract base class
│   │   ├── sky_scraper.py
│   │   ├── bt_scraper.py
│   │   ├── ee_scraper.py
│   │   ├── hyperoptic_scraper.py
│   │   ├── virgin_scraper.py
│   │   └── vodafone_scraper.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── browser_utils.py    # Playwright helpers
│   │   ├── data_processor.py   # Data cleaning/validation
│   │   └── exporter.py         # Export functionality
│   └── models/
│       ├── __init__.py
│       └── broadband_deal.py   # Data models
├── tests/
│   ├── __init__.py
│   ├── test_scrapers.py
│   └── test_data_processor.py
├── output/
│   └── .gitkeep
└── logs/
    └── .gitkeep
```

---

## 9. Functional Requirements

### 9.1 Core Features

**FR-1: Postcode Input**
- System shall accept UK postcodes in standard formats
- System shall validate postcode format before processing
- System shall handle both uppercase and lowercase inputs

**FR-2: Provider Selection**
- System shall allow selection of specific providers or all providers
- System shall maintain provider configuration in external files
- System shall support easy addition of new providers

**FR-3: Cookie Handling**
- System shall automatically detect cookie consent banners
- System shall click "Reject All" or equivalent option
- System shall timeout and continue if cookie banner not found (with warning)

**FR-4: Address Selection**
- System shall retrieve all available addresses for given postcode
- System shall allow selection of specific address or use first available
- System shall handle scenarios where address is not available

**FR-5: Form Automation**
- System shall complete all mandatory form fields
- System shall use sensible defaults for optional fields
- System shall handle different form types across providers

**FR-6: Data Extraction**
- System shall extract all metrics defined in section 6.1
- System shall handle missing data gracefully
- System shall retry failed extractions up to 3 times

**FR-7: Data Export**
- System shall export data to CSV format (minimum requirement)
- System shall support Excel (.xlsx) format
- System shall support JSON format for API integration
- System shall include timestamp and metadata in exports

**FR-8: Error Handling**
- System shall log all errors with appropriate severity levels
- System shall continue processing other providers if one fails
- System shall generate error report summary

**FR-9: Logging**
- System shall log all significant actions
- System shall include timestamps in all log entries
- System shall support different log levels (DEBUG, INFO, WARNING, ERROR)

### 9.2 Non-Functional Requirements

**NFR-1: Performance**
- Maximum execution time: 5 minutes per provider
- Support concurrent scraping of multiple providers
- Efficient memory usage (< 500MB per browser instance)

**NFR-2: Reliability**
- Graceful handling of network issues
- Automatic retry mechanism for transient failures
- Data integrity validation

**NFR-3: Maintainability**
- Modular code structure
- Comprehensive inline documentation
- Configuration-driven approach for easy updates

**NFR-4: Scalability**
- Easy addition of new providers
- Support for batch processing multiple postcodes
- Configurable concurrency levels

**NFR-5: Security**
- No storage of personal information
- Secure handling of temporary data
- Compliance with web scraping best practices

---

## 10. Risk Assessment

### 10.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Website structure changes | High | High | Regular maintenance schedule, flexible selectors |
| Anti-scraping measures | High | Medium | User-agent rotation, rate limiting, respectful scraping |
| Dynamic content loading | Medium | High | Appropriate wait strategies, async handling |
| Cookie consent variations | Medium | Medium | Multiple selector strategies, fallback options |
| Address lookup failures | Medium | Low | Error handling, user notification |

### 10.2 Business Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Legal challenges | High | Low | Terms of service review, consultation with legal |
| Data accuracy issues | High | Medium | Validation checks, manual spot-checks |
| Provider blocking | High | Low | Respectful rate limiting, monitoring |

---

## 11. Compliance and Legal Considerations

### 11.1 Web Scraping Ethics
- Implement respectful rate limiting (minimum 2-3 seconds between requests)
- Include appropriate User-Agent headers
- Honor robots.txt directives
- Review each provider's Terms of Service

### 11.2 Data Protection
- Do not store personal identifiable information (PII)
- Clear temporary data after processing
- Secure handling of postcodes and addresses

### 11.3 Usage Terms
- Tool for personal/research use only (unless licensed)
- No automated commercial use without authorization
- Respect intellectual property rights

---

## 12. Testing Strategy

### 12.1 Test Cases

**Unit Tests:**
- Data validation functions
- Data transformation functions
- Export formatting

**Integration Tests:**
- Browser automation flows
- End-to-end scraping for each provider
- Data export functionality

**Test Scenarios:**
- Valid postcode with multiple addresses
- Valid postcode with single address
- Invalid postcode format
- Postcode with no broadband availability
- Network timeout scenarios
- Unexpected page structure changes

### 12.2 Test Data
- Sample postcodes covering different UK regions
- Known addresses with available broadband
- Edge cases (new builds, rural areas, city centers)

---

## 13. Deliverables

### 13.1 Software Deliverables
1. Complete Python application with all modules
2. Requirements.txt with all dependencies
3. Configuration files for all providers
4. Installation and setup guide
5. User manual
6. API documentation (if applicable)

### 13.2 Documentation Deliverables
1. Technical documentation
2. Provider configuration guide
3. Troubleshooting guide
4. Maintenance manual
5. Test reports

### 13.3 Output Deliverables
1. CSV export functionality
2. Excel export functionality
3. JSON export functionality
4. Sample output files
5. Data dictionary

---

## 14. Implementation Phases

### Phase 1: Foundation (Week 1-2)
- Set up project structure
- Install and configure Playwright
- Implement base scraper class
- Create data models
- Set up logging and error handling

### Phase 2: Core Scraping (Week 3-5)
- Implement scraper for Sky
- Implement scraper for BT
- Implement scraper for EE
- Implement scraper for Hyperoptic
- Implement scraper for Virgin Media
- Implement scraper for Vodafone

### Phase 3: Data Processing (Week 6)
- Implement data validation
- Implement data normalization
- Create export functionality
- Add reporting features

### Phase 4: Testing and Refinement (Week 7-8)
- Conduct comprehensive testing
- Fix identified issues
- Optimize performance
- Refine error handling

### Phase 5: Documentation and Deployment (Week 9)
- Complete documentation
- Create user guides
- Prepare deployment package
- Conduct final validation

---

## 15. Maintenance and Support

### 15.1 Ongoing Maintenance
- Monthly website structure checks
- Quarterly dependency updates
- Immediate fixes for breaking changes
- Performance monitoring and optimization

### 15.2 Update Schedule
- **Weekly:** Monitor for major provider website changes
- **Monthly:** Review and update selectors if needed
- **Quarterly:** Update dependencies and security patches
- **Annually:** Comprehensive review and refactoring

---

## 16. Appendices

### Appendix A: Provider URLs and Navigation Paths
*To be completed with specific provider information*

### Appendix B: Sample Configuration Files
*To be included with example provider configurations*

### Appendix C: Sample Output Data
*To be included with example CSV/Excel exports*

### Appendix D: Key Metrics Reference Screenshot
*[Screenshot to be attached showing required metrics]*

### Appendix E: Error Codes and Messages
*To be completed during implementation*

### Appendix F: Glossary
- **FTTC**: Fiber to the Cabinet
- **FTTP**: Fiber to the Premises
- **Mbps**: Megabits per second
- **ISP**: Internet Service Provider
- **CSS Selector**: Pattern used to identify HTML elements
- **XPath**: Query language for selecting nodes in XML/HTML

---

## 17. Approval and Sign-off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Project Sponsor | | | |
| Technical Lead | | | |
| QA Lead | | | |

---

## Document Control

**Change History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 03-Feb-2026 | System | Initial draft |

---

**Next Steps:**
1. Review and approve requirements document
2. Provide specific provider URLs and navigation details
3. Attach screenshot showing required metrics
4. Define specific address selection logic
5. Confirm export format specifications
6. Begin Phase 1 implementation

