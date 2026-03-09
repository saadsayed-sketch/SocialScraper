"""
Browser management for social media scraping with URL extraction focus
"""
import asyncio
import random
from typing import Dict, Optional, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright
from .config import ScrapingConfig


class BrowserManager:
    """Browser manager optimized for URL discovery and extraction"""
    
    def __init__(self, config: ScrapingConfig):
        self.config = config
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self._contexts: Dict[str, BrowserContext] = {}
        self.session_path = "sessions"  # Directory for session storage
        self._current_page: Optional[Page] = None
    
    async def initialize(self) -> None:
        """Initialize Playwright and browser with anti-detection settings"""
        if self.playwright is None:
            self.playwright = await async_playwright().start()
            
        if self.browser is None:
            # Launch browser with enhanced anti-detection settings for Cloudflare
            self.browser = await self.playwright.chromium.launch(
                headless=self.config.headless,
                args=[
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-infobars',
                    '--window-position=0,0',
                    '--ignore-certifcate-errors',
                    '--ignore-certifcate-errors-spki-list',
                    '--disable-blink-features=AutomationControlled',
                    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                ]
            )
    
    async def create_context(self, platform: str, session_path: Optional[str] = None) -> BrowserContext:
        """Create browser context optimized for URL detection and extraction"""
        if not self.browser:
            await self.initialize()
        
        # Create context with stealth settings
        context_options = {
            'viewport': self.config.viewport,
            'user_agent': self._get_random_user_agent(),
            'java_script_enabled': True,
            'accept_downloads': False,  # Focus on URL extraction, not downloads
            'ignore_https_errors': True,  # Handle sites with SSL issues
        }
        
        # Add session storage if provided
        if session_path:
            context_options['storage_state'] = session_path
        
        context = await self.browser.new_context(**context_options)
        
        # Apply anti-detection measures
        await self._apply_stealth_settings(context)
        
        # Store context for reuse
        self._contexts[platform] = context
        
        return context
    
    async def get_page(self) -> Page:
        """Get a page for scraping (creates new context if needed)"""
        if not self.browser:
            await self.initialize()
        
        # Create default context if none exists
        if 'default' not in self._contexts:
            await self.create_context('default')
        
        context = self._contexts['default']
        
        # Create new page if none exists or reuse current
        if not self._current_page:
            self._current_page = await self.create_page_for_url_extraction(context)
        
        return self._current_page
    
    async def save_session(self, session_file: str) -> None:
        """Save current session state to file"""
        try:
            import os
            import json
            
            # Ensure session directory exists
            os.makedirs(os.path.dirname(session_file), exist_ok=True)
            
            # Get current context
            if 'default' in self._contexts:
                context = self._contexts['default']
                storage_state = await context.storage_state()
                
                with open(session_file, 'w') as f:
                    json.dump(storage_state, f)
                    
                print(f"Session saved to {session_file}")
        except Exception as e:
            print(f"Failed to save session: {e}")
    
    async def load_session(self, session_file: str) -> bool:
        """Load session state from file"""
        try:
            import os
            import json
            
            if not os.path.exists(session_file):
                return False
            
            with open(session_file, 'r') as f:
                storage_state = json.load(f)
            
            # Create context with loaded session
            if not self.browser:
                await self.initialize()
            
            context = await self.browser.new_context(
                viewport=self.config.viewport,
                user_agent=self._get_random_user_agent(),
                storage_state=storage_state
            )
            
            await self._apply_stealth_settings(context)
            self._contexts['default'] = context
            
            # Create page
            self._current_page = await self.create_page_for_url_extraction(context)
            
            print(f"Session loaded from {session_file}")
            return True
            
        except Exception as e:
            print(f"Failed to load session: {e}")
            return False
    
    async def get_context(self, platform: str) -> Optional[BrowserContext]:
        """Get existing context for platform"""
        return self._contexts.get(platform)
    
    async def create_page_for_url_extraction(self, context: BrowserContext) -> Page:
        """Create page optimized for URL extraction"""
        page = await context.new_page()
        
        # Set timeouts for URL-focused scraping
        page.set_default_timeout(self.config.page_timeout)
        page.set_default_navigation_timeout(self.config.page_timeout)
        
        # Block unnecessary resources to focus on content and URLs
        await page.route("**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2}", 
                        lambda route: route.abort())
        await page.route("**/ads/**", lambda route: route.abort())
        await page.route("**/analytics/**", lambda route: route.abort())
        
        # Add URL extraction helpers to page (inject after page creation)
        await page.evaluate("""
            window.extractURLsFromElement = (element) => {
                const urls = new Set();
                
                // Get all links within element
                element.querySelectorAll('a[href]').forEach(link => {
                    if (link.href.startsWith('http')) {
                        urls.add(link.href);
                    }
                });
                
                // Extract URLs from text content
                const text = element.textContent || '';
                const urlRegex = /https?:\\/\\/[^\\s<>"{}|\\\\^`[\\]]+/g;
                const matches = text.match(urlRegex) || [];
                matches.forEach(url => urls.add(url));
                
                return Array.from(urls);
            };
            
            window.isURLElement = (element) => {
                if (!element) return false;
                return element.tagName === 'A' || 
                       element.getAttribute('data-testid')?.includes('link') ||
                       element.getAttribute('data-testid')?.includes('url') ||
                       (element.textContent && element.textContent.match(/https?:\\/\\//)) !== null;
            };
        """)
        
        return page
    
    async def navigate_with_url_focus(self, page: Page, url: str) -> bool:
        """Navigate to URL with focus on link detection"""
        try:
            # Add random delay to mimic human behavior
            await asyncio.sleep(random.uniform(self.config.min_delay, self.config.max_delay))
            
            # Navigate and wait for content that might contain URLs
            await page.goto(url, wait_until='domcontentloaded')
            
            # Wait for potential dynamic content with URLs
            await page.wait_for_timeout(random.randint(1000, 3000))
            
            return True
            
        except Exception as e:
            print(f"Navigation failed for {url}: {e}")
            return False
    
    async def extract_urls_from_page(self, page: Page) -> List[str]:
        """Extract all URLs from current page"""
        try:
            # Use injected JavaScript to extract URLs
            urls = await page.evaluate("""
                () => {
                    const urls = new Set();
                    
                    // Extract from anchor tags
                    document.querySelectorAll('a[href]').forEach(link => {
                        const href = link.href;
                        if (href && href.startsWith('http')) {
                            urls.add(href);
                        }
                    });
                    
                    // Extract from text content using regex
                    const textContent = document.body.innerText || '';
                    const urlRegex = /https?:\\/\\/[^\\s<>"{}|\\\\^`[\\]]+/g;
                    const textUrls = textContent.match(urlRegex) || [];
                    textUrls.forEach(url => urls.add(url));
                    
                    // Extract from specific social media elements
                    document.querySelectorAll('[data-testid*="url"], [data-testid*="link"]').forEach(el => {
                        const href = el.getAttribute('href') || el.textContent;
                        if (href && href.startsWith('http')) {
                            urls.add(href);
                        }
                    });
                    
                    return Array.from(urls);
                }
            """)
            
            return urls
            
        except Exception as e:
            print(f"URL extraction failed: {e}")
            return []
    
    async def wait_for_url_content(self, page: Page, timeout: int = 5000) -> bool:
        """Wait for content that likely contains URLs to load"""
        try:
            # Wait for common elements that contain URLs
            await page.wait_for_selector(
                'a[href*="http"], [data-testid*="link"], [data-testid*="url"]',
                timeout=timeout
            )
            return True
        except:
            # If no URL elements found, still return True to continue
            return True
    
    async def _apply_stealth_settings(self, context: BrowserContext) -> None:
        """Apply enhanced anti-detection measures to bypass Cloudflare"""
        # Remove webdriver property
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)
        
        # Override automation indicators
        await context.add_init_script("""
            // Remove automation flags
            delete navigator.__proto__.webdriver;
            
            // Override chrome property
            window.chrome = {
                runtime: {},
            };
            
            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
        """)
        
        # Override permissions
        await context.add_init_script("""
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        # Randomize screen properties
        screen_width = random.randint(1200, 1920)
        screen_height = random.randint(800, 1080)
        
        await context.add_init_script(f"""
            Object.defineProperty(screen, 'width', {{
                get: () => {screen_width},
            }});
            Object.defineProperty(screen, 'height', {{
                get: () => {screen_height},
            }});
        """)
        
        # Add realistic mouse movements and timing
        await context.add_init_script("""
            // Override Date to avoid timezone detection
            const originalDate = Date;
            Date = class extends originalDate {
                getTimezoneOffset() {
                    return 0; // UTC
                }
            };
            
            // Add realistic timing
            const originalSetTimeout = window.setTimeout;
            window.setTimeout = function(callback, delay) {
                const jitter = Math.random() * 10;
                return originalSetTimeout(callback, delay + jitter);
            };
        """)
    
    async def _inject_url_extraction_helpers(self, page: Page) -> None:
        """Inject JavaScript helpers for URL extraction"""
        await page.add_init_script("""
            window.extractURLsFromElement = (element) => {
                const urls = new Set();
                
                // Get all links within element
                element.querySelectorAll('a[href]').forEach(link => {
                    if (link.href.startsWith('http')) {
                        urls.add(link.href);
                    }
                });
                
                // Extract URLs from text content
                const text = element.textContent || '';
                const urlRegex = /https?:\\/\\/[^\\s<>"{}|\\\\^`[\\]]+/g;
                const matches = text.match(urlRegex) || [];
                matches.forEach(url => urls.add(url));
                
                return Array.from(urls);
            };
            
            window.isURLElement = (element) => {
                return element.tagName === 'A' || 
                       element.getAttribute('data-testid')?.includes('link') ||
                       element.getAttribute('data-testid')?.includes('url') ||
                       element.textContent?.match(/https?:\\/\\//) !== null;
            };
        """)
    
    def _get_random_user_agent(self) -> str:
        """Get random user agent for anti-detection"""
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
        ]
        return random.choice(user_agents)
    
    async def close_context(self, platform: str) -> None:
        """Close browser context for specific platform"""
        if platform in self._contexts:
            await self._contexts[platform].close()
            del self._contexts[platform]
    
    async def close(self) -> None:
        """Close all browser resources"""
        # Close all contexts
        for context in self._contexts.values():
            await context.close()
        self._contexts.clear()
        
        # Close browser
        if self.browser:
            await self.browser.close()
            self.browser = None
        
        # Stop playwright
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None