# Project Structure

## Directory Organization

```
├── core/                   # Core functionality and shared components
│   ├── models.py          # Simplified data models (CSEProfile only)
│   ├── config.py          # Configuration management for all platforms
│   ├── browser.py         # Browser automation and session management
│   ├── cse_handler.py     # CSE profile handling
│   └── session_manager.py # Session management
├── platforms/             # Platform-specific scrapers
│   ├── reddit.py          # Reddit scraper
│   ├── instagram.py       # Instagram scraper
│   └── x.py              # X (Twitter) scraper
├── utils/                 # Utility functions and helpers
│   ├── generate_search_keywords.py  # AI keyword generation
│   └── similarity.py      # Similarity filtering
├── main_instagram.py      # Simplified Instagram main script
├── main_reddit.py         # Simplified Reddit main script
├── main_x.py             # Simplified X main script
├── sessions/              # Browser session storage (JSON files)
├── persistent_sessions/   # Persistent session storage by platform
└── .env                   # Environment variables (credentials)
```

## Key Architectural Principles

### Core Module (`core/`)
- **models.py** - Simplified CSEProfile model only
- **config.py** - Platform-specific configuration classes with CSS selectors
- **browser.py** - Shared browser automation and session management
- **cse_handler.py** - CSE profile loading and validation
- **session_manager.py** - Session persistence management

### Platform Modules (`platforms/`)
- Each platform has dedicated scraper class
- Platform-specific authentication handled within scraper
- All inherit common patterns but implement platform-specific logic
- Focus on account search and phishing detection

### Main Scripts (Simplified)
- **main_instagram.py** - Just provide CSE name, auto-generates profile
- **main_reddit.py** - Just provide CSE name, auto-generates profile
- **main_x.py** - Just provide CSE name, auto-generates profile
- No complex input required - single command line argument

### Session Management
- `sessions/` - JSON files for browser session persistence
- `persistent_sessions/` - Platform-specific session storage
- Enables authentication persistence across runs

### Configuration Patterns
- Dataclass-based configuration with sensible defaults
- Platform-specific CSS selectors and timing settings
- Auto-generated domains and keywords from CSE name

## File Naming Conventions
- Snake_case for Python files and directories
- Platform names: `reddit.py`, `instagram.py`, `x.py`
- Main scripts: `main_instagram.py`, `main_reddit.py`, `main_x.py`
- Config classes: `ScrapingConfig`, `RedditConfig`, etc.