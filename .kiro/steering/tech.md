# Technology Stack

## Core Technologies
- **Python 3.8+** - Primary language
- **Playwright** - Browser automation and web scraping
- **asyncio** - Asynchronous operations for concurrent scraping
- **dataclasses** - Data models and configuration management

## Dependencies
- `playwright==1.40.0` - Browser automation
- `pytest==7.4.3` - Testing framework
- `pytest-asyncio==0.21.1` - Async test support
- `python-dotenv==1.0.0` - Environment variable management

## Architecture Patterns
- **Async/await throughout** - All scraping operations are asynchronous
- **Dataclass models** - Structured data representation with `@dataclass`
- **Platform abstraction** - Unified interface via `UnifiedScraper`
- **Configuration management** - Centralized config classes
- **Session persistence** - Browser session storage for authentication

## Common Commands

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install

# Install package in development mode
pip install -e .
```

### Testing
```bash
# Run tests
pytest -v --asyncio-mode=auto

# Run demo script
python demo_reddit_login_url_scraping.py
```

### Development
- Use async/await patterns consistently
- Follow dataclass patterns for models
- Maintain session persistence for authentication
- Focus on URL extraction and phishing detection