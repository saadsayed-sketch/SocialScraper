# Social Media Scraper - Phishing Account Detection System

A browser automation system for detecting phishing accounts across social media platforms. Supports Reddit, Instagram, and X (Twitter) with focus on identifying accounts that impersonate Critical Sector Entities (CSEs).

**Note**: This system has been transformed from URL-focused scraping to account-focused phishing detection.

## Features

- **Multi-Platform Account Detection**: Detect suspicious accounts on Reddit, Instagram, and X (Twitter)
- **CSE Profile Management**: Process Critical Sector Entity profiles for targeted monitoring
- **Phishing Account Analysis**: Advanced similarity analysis and risk scoring
- **Session Management**: Persistent login sessions with security-first approach
- **Manual Authentication**: Secure login process with automatic session persistence
- **Risk Assessment**: Comprehensive threat analysis and actionable reporting

## Project Structure

```
├── core/                   # Core functionality and shared components
│   ├── __init__.py
│   ├── models.py          # Data models (CSEProfile, Account, AnalysisResult)
│   ├── config.py          # Configuration management for all platforms
│   ├── browser.py         # Browser automation and session management
│   ├── session_manager.py # Enhanced session management with persistence
│   ├── cse_handler.py     # CSE profile input and processing
│   ├── analyzer.py        # Account analysis and similarity detection
│   ├── detection_engine.py # Main orchestrator for phishing detection
│   └── unified_scraper.py # Legacy - maintained for compatibility
├── platforms/             # Platform-specific account detection modules
│   ├── __init__.py
│   ├── base.py           # Base platform module interface
│   ├── reddit.py         # Reddit account detection and analysis
│   ├── instagram.py      # Instagram account detection and analysis
│   └── x.py             # X (Twitter) account detection and analysis
├── utils/                # Utility functions and helpers
│   └── __init__.py
├── sessions/             # Browser session storage (legacy)
├── persistent_sessions/  # Secure persistent session storage by platform
├── examples/             # Usage examples and demonstrations
│   └── authentication_example.py  # Authentication and session demo
├── tests/                # Test suite for account detection functionality
├── .env                  # Environment variables (DISABLED for security)
├── requirements.txt      # Python dependencies
├── setup.py             # Package setup
├── pytest.ini          # Test configuration
└── demo_*.py           # Demonstration scripts
```

## Demo Scripts

The system includes comprehensive demonstration scripts:

### Core Demos
- **`demo_complete_workflow.py`** - Complete end-to-end phishing detection workflow
- **`demo_cse_phishing_detection.py`** - Comprehensive CSE processing and multi-entity analysis
- **`demo_cse_input_workflow.py`** - CSE profile creation, validation, and processing

### Platform-Specific Demos
- **`demo_reddit_login_url_scraping.py`** - Reddit account detection with session persistence
- **`demo_instagram_scraper.py`** - Instagram account detection and analysis

### Authentication Demo
- **`examples/authentication_example.py`** - Session management and manual login process

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install Playwright browsers:
```bash
playwright install
```

3. Install package in development mode:
```bash
pip install -e .
```

## Quick Start

### Complete Workflow Demo

Run the complete workflow demonstration:
```bash
python demo_complete_workflow.py
```

This shows the entire process from CSE profile setup to threat detection.

### CSE Profile Input Demo

See how to create and process CSE profiles:
```bash
python demo_cse_input_workflow.py
```

### Platform-Specific Detection

Test individual platform detection:
```bash
python demo_reddit_login_url_scraping.py
python demo_instagram_scraper.py
```

### Authentication and Session Management

Learn about the authentication system:
```bash
python examples/authentication_example.py
```

## Usage Examples

### Basic Account Detection

```python
import asyncio
from core.detection_engine import AccountDetectionEngine
from core.browser import BrowserManager
from core.config import ConfigManager
from core.models import CSEProfile

async def detect_phishing_accounts():
    # Create CSE profile
    cse_profile = CSEProfile(
        entity_id="bank_001",
        entity_name="First National Bank",
        entity_type="financial",
        official_accounts={
            "reddit": "FirstNationalBank",
            "instagram": "firstnationalbank_official"
        },
        search_keywords=["first", "national", "bank"]
    )
    
    # Initialize detection engine
    config_manager = ConfigManager()
    base_config, _ = config_manager.get_reddit_config()
    browser_manager = BrowserManager(base_config)
    detection_engine = AccountDetectionEngine(browser_manager, base_config)
    
    # Detect phishing accounts
    await browser_manager.initialize()
    results = await detection_engine.detect_phishing_accounts([cse_profile])
    
    # Analyze results
    for result in results:
        high_risk_accounts = result.get_high_risk_accounts()
        print(f"Found {len(high_risk_accounts)} high-risk accounts")
    
    await browser_manager.close()

asyncio.run(detect_phishing_accounts())
```

### Manual Authentication

```python
import asyncio
from platforms.reddit import RedditScraper
from core.browser import BrowserManager
from core.config import ConfigManager

async def authenticate_manually():
    config_manager = ConfigManager()
    base_config, reddit_config = config_manager.get_reddit_config()
    browser_manager = BrowserManager(base_config)
    
    await browser_manager.initialize()
    reddit_module = RedditScraper(browser_manager, reddit_config)
    
    # Check for existing session
    if await reddit_module.session_manager.check_existing_session('reddit'):
        print("✓ Using existing session")
        await reddit_module.login_with_persistence()
    else:
        print("Manual login required")
        # In real usage: await reddit_module.login(username, password)
        # Session will be automatically saved
    
    await browser_manager.close()

asyncio.run(authenticate_manually())
```

## Security Features

### Authentication Security
- **Automatic login disabled by default** - No environment variable usage
- **Manual login required** - Secure credential handling
- **Session persistence** - Automatic session saving and loading
- **Session validation** - Automatic validation before operations
- **Graceful fallback** - Manual login when sessions expire

### Account Detection Security
- **Risk-based analysis** - Comprehensive threat scoring
- **Suspicious indicator detection** - Multiple phishing pattern recognition
- **Cross-platform correlation** - Account relationship analysis
- **Actionable reporting** - Clear threat prioritization

## Configuration

### Platform Settings

Each platform module inherits from `BasePlatformModule` and implements:
- Account search functionality
- Profile data extraction
- Platform-specific analysis methods
- Session management integration

### CSE Profile Format

```python
CSEProfile(
    entity_id="unique_identifier",
    entity_name="Organization Name",
    entity_type="financial|government|infrastructure",
    official_accounts={
        "reddit": "official_username",
        "instagram": "official_username",
        "x": "official_username"
    },
    key_personnel=["Name 1", "Name 2"],
    official_domains=["domain1.com", "domain2.com"],
    sector_classification="banking|energy|government",
    search_keywords=["keyword1", "keyword2"]
)
```

## Testing

Run the test suite:
```bash
pytest -v --asyncio-mode=auto
```

Run specific test categories:
```bash
# Test data models
pytest tests/test_models.py -v

# Test session management
pytest tests/test_session_manager.py -v

# Test complete workflow integration
pytest tests/test_complete_workflow_integration.py -v
```

## Key Changes from URL Scraping

### What Changed
- **Focus shifted** from URL extraction to account detection
- **CSE profiles** replace generic search queries
- **Account analysis** replaces URL analysis
- **Risk scoring** for phishing accounts
- **Manual authentication** for security
- **Session persistence** for continuous monitoring

### What Stayed
- Browser automation infrastructure
- Multi-platform support
- Async operation patterns
- Session management (enhanced)
- Configuration system

## Demo Script Features

Each demo script demonstrates specific aspects:

1. **Complete Workflow** - End-to-end detection process
2. **CSE Processing** - Profile creation and validation
3. **Authentication** - Session management and manual login
4. **Platform Detection** - Platform-specific account analysis
5. **Risk Assessment** - Threat analysis and reporting

## Contributing

1. Follow the established patterns in platform modules
2. Focus on account detection and phishing analysis
3. Maintain async/await patterns throughout
4. Ensure security-first authentication approach
5. Add comprehensive tests for new features
6. Update demo scripts for new functionality

## License

This project is for educational and security research purposes. Ensure compliance with platform terms of service and applicable laws when using for account detection activities.