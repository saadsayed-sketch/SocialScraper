"""
Facebook scraper - Basic account search and URL collection
"""
import asyncio
import json
import os
from datetime import datetime
from typing import List, Optional
from playwright.async_api import Page

from core.browser import BrowserManager
from core.config import FacebookConfig


class FacebookScraper:
    """Basic Facebook scraper for searching accounts and collecting URLs"""
    
    def __init__(self, browser_manager: BrowserManager, facebook_config: FacebookConfig):
        self.browser_manager = browser_manager
        self.facebook_config = facebook_config
        self._page: Optional[Page] = None
        self._context = None
    
    async def initialize(self):
        """Initialize browser context and page"""
        if not self._context:
            self._context = await self.browser_manager.create_context("facebook")
            self._page = await self.browser_manager.create_page_for_url_extraction(self._context)
    
    async def login_with_session(self) -> bool:
        """Login using saved session from persistent storage"""
        try:
            # Check for persistent session first
            persistent_session_path = "./persistent_sessions/facebook"
            session_file = "./sessions/facebook_session.json"
            
            # Try persistent session first (preferred)
            if os.path.exists(persistent_session_path) and os.path.isdir(persistent_session_path):
                print("🔄 Loading persistent session...")
                # Check if it has content
                if len(os.listdir(persistent_session_path)) > 0:
                    self._context = await self.browser_manager.create_context("facebook", session_path=session_file)
                    self._page = await self.browser_manager.create_page_for_url_extraction(self._context)
                    
                    # Test if session is valid
                    await self._page.goto(self.facebook_config.base_url)
                    await asyncio.sleep(3)
                    
                    if await self._is_logged_in():
                        print("✅ Facebook persistent session loaded successfully")
                        return True
            
            # Fallback to JSON session file
            if os.path.exists(session_file):
                print("🔄 Loading session from JSON...")
                self._context = await self.browser_manager.create_context("facebook", session_path=session_file)
                self._page = await self.browser_manager.create_page_for_url_extraction(self._context)
                
                # Test if session is valid
                await self._page.goto(self.facebook_config.base_url)
                await asyncio.sleep(3)
                
                if await self._is_logged_in():
                    print("✅ Facebook session loaded successfully")
                    return True
            
            print("❌ No saved session found.")
            print("   Please run: python facebook_manual_login.py")
            return False
                
        except Exception as e:
            print(f"Failed to load session: {e}")
            return False
    
    async def login_interactive(self) -> bool:
        """
        Interactive manual login - opens browser for user to login
        Saves session to persistent storage
        """
        try:
            print("\n" + "=" * 60)
            print("Facebook Manual Login Required")
            print("=" * 60)
            print("\nA browser window will open for you to login.")
            print("Please login manually, then the scraper will continue.")
            print("\n⚠️  DO NOT CLOSE THE BROWSER WINDOW!")
            print("=" * 60)
            
            input("\nPress Enter to open browser for login...")
            
            # Create persistent session directory
            persistent_session_path = "./persistent_sessions/facebook"
            os.makedirs(persistent_session_path, exist_ok=True)
            
            # Import playwright for persistent context
            from playwright.async_api import async_playwright
            
            playwright = await async_playwright().start()
            
            # Launch browser with persistent context
            browser = await playwright.chromium.launch_persistent_context(
                user_data_dir=persistent_session_path,
                headless=False,
                viewport={'width': 1920, 'height': 1080},
                args=[
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-blink-features=AutomationControlled'
                ]
            )
            
            # Get or create page
            if len(browser.pages) > 0:
                page = browser.pages[0]
            else:
                page = await browser.new_page()
            
            # Navigate to Facebook
            print("\n🌐 Opening Facebook...")
            await page.goto(self.facebook_config.base_url)
            await asyncio.sleep(3)
            
            print("\n" + "=" * 60)
            print("✋ PLEASE LOGIN IN THE BROWSER")
            print("=" * 60)
            print("\nSteps:")
            print("1. Enter your email/phone and password")
            print("2. Complete any 2FA or verification")
            print("3. Wait until you see your news feed")
            print("4. Come back here and press Enter")
            print("\n⚠️  DO NOT CLOSE THE BROWSER!")
            print("=" * 60)
            
            input("\nPress Enter after you've logged in...")
            
            # Verify login
            print("\n🔍 Verifying login...")
            await asyncio.sleep(2)
            
            # Check for logged-in indicators
            logged_in = await self._is_logged_in_page(page)
            
            if logged_in:
                print("✅ Login verified!")
                
                # Save to JSON session as well
                sessions_dir = "./sessions"
                os.makedirs(sessions_dir, exist_ok=True)
                session_file = f"{sessions_dir}/facebook_session.json"
                await browser.storage_state(path=session_file)
                
                print(f"✅ Session saved to persistent storage")
                print(f"✅ Session backup saved to {session_file}")
                
                # Close the login browser
                await browser.close()
                await playwright.stop()
                
                # Now initialize the scraper with the saved session
                print("\n🔄 Initializing scraper with saved session...")
                return await self.login_with_session()
            else:
                print("⚠️  Could not verify login.")
                await browser.close()
                await playwright.stop()
                return False
                
        except Exception as e:
            print(f"Interactive login error: {e}")
            return False
    
    async def _is_logged_in(self) -> bool:
        """Check if currently logged in"""
        return await self._is_logged_in_page(self._page)
    
    async def _is_logged_in_page(self, page: Page) -> bool:
        """Check if page is logged in"""
        try:
            # Look for navigation elements that only appear when logged in
            nav_selectors = [
                "[aria-label='Home']",
                "[aria-label='Your profile']",
                "[aria-label='Account']",
                "div[role='navigation']"
            ]
            
            for selector in nav_selectors:
                element = await page.query_selector(selector)
                if element:
                    return True
            
            return False
        except:
            return False
    
    async def ensure_logged_in(self) -> bool:
        """
        Ensure user is logged in - automatically handles login if needed
        Returns True if logged in successfully, False otherwise
        """
        # Try to login with existing session
        if await self.login_with_session():
            return True
        
        # No session found, prompt for interactive login
        print("\n" + "=" * 60)
        print("⚠️  No saved Facebook session found")
        print("=" * 60)
        print("\nYou need to login to Facebook to use the scraper.")
        
        response = input("\nWould you like to login now? (y/n): ").strip().lower()
        
        if response == 'y' or response == 'yes':
            return await self.login_interactive()
        else:
            print("\n❌ Cannot proceed without login.")
            return False
    
    async def search_and_collect_accounts(self, cse_name: str, output_file: str = None) -> List[dict]:
        """
        Search for CSE name and collect account URLs
        
        Args:
            cse_name: Name to search for
            output_file: JSON file to save results (optional)
            
        Returns:
            List of account dictionaries with username and URL
        """
        try:
            if not self._page:
                print("❌ Not initialized. Please login first.")
                return []
            
            print(f"🔍 Searching for: {cse_name}")
            
            # Go to Facebook home first
            await self._page.goto(f"{self.facebook_config.base_url}/")
            await asyncio.sleep(2)
            
            # Find and click on search box
            search_box = await self._page.wait_for_selector("input[type='search'], input[placeholder*='Search']", timeout=10000)
            await search_box.click()
            await asyncio.sleep(1)
            
            # Type search query
            await search_box.fill(cse_name)
            await asyncio.sleep(1)
            
            # Press Enter to search
            await search_box.press("Enter")
            await asyncio.sleep(4)  # Wait longer for results to load
            
            # Try to click on "Pages" tab to filter results
            try:
                # Wait a bit for tabs to appear
                await asyncio.sleep(2)
                
                # Try multiple selectors for Pages tab
                pages_tab_selectors = [
                    "a[href*='/search/pages']",
                    "span:has-text('Pages')",
                    "div[role='tab']:has-text('Pages')",
                ]
                
                for selector in pages_tab_selectors:
                    try:
                        pages_tab = await self._page.query_selector(selector)
                        if pages_tab:
                            await pages_tab.click()
                            print("   Clicked on Pages tab")
                            await asyncio.sleep(3)
                            break
                    except:
                        continue
                else:
                    print("   ⚠️ Could not find Pages tab, using default results")
            except Exception as e:
                print(f"   ⚠️ Could not filter by Pages: {e}")
            
            # Collect account URLs from search results
            accounts = await self._extract_account_urls_from_search()
            
            print(f"✅ Found {len(accounts)} accounts")
            
            # Save to JSON if output file specified
            if output_file:
                self._save_to_json(accounts, output_file, cse_name)
            
            return accounts
            
        except Exception as e:
            print(f"Search error: {e}")
            return []
    
    async def _extract_account_urls_from_search(self) -> List[dict]:
        """Extract account URLs from search results"""
        try:
            accounts = []
            seen_urls = set()

            # Wait for search results to load
            await asyncio.sleep(3)

            print("   Looking for search results...")

            # Scroll down a bit to load more results
            try:
                await self._page.evaluate("window.scrollBy(0, 300)")
                await asyncio.sleep(2)
            except:
                pass

            # Look for search result items specifically
            # Facebook search results are typically in divs with specific patterns
            result_selectors = [
                "div[role='article']",  # Article containers (common for search results)
                "div[data-pagelet*='SearchResult']",  # Search result pagelets
                "div[class*='search']",  # Divs with 'search' in class name
            ]
            
            result_containers = []
            for selector in result_selectors:
                try:
                    containers = await self._page.query_selector_all(selector)
                    if containers and len(containers) > 0:
                        result_containers.extend(containers)
                        print(f"   Found {len(containers)} result containers with selector: {selector}")
                except:
                    continue
            
            if not result_containers:
                print("   ⚠️  No result containers found, trying all links")
                # Fallback: get all links from main area
                all_links = await self._page.query_selector_all("a[href]")
            else:
                # Extract links from result containers
                all_links = []
                for container in result_containers:
                    links = await container.query_selector_all("a[href]")
                    all_links.extend(links)
            
            print(f"   Found {len(all_links)} total links to process")

            # Process each link
            for link in all_links[:50]:  # Check up to 50 links
                try:
                    href = await link.get_attribute('href')
                    if not href:
                        continue

                    # Parse Facebook URL
                    url = href
                    if not url.startswith('http'):
                        url = f"{self.facebook_config.base_url}{href}"
                    
                    # Must contain facebook.com
                    if 'facebook.com' not in url:
                        continue
                    
                    # Skip non-profile URLs
                    excluded_patterns = [
                        '/search/', '/groups/', '/events/', '/marketplace/', 
                        '/watch/', '/gaming/', '/pages/category/', '/hashtag/',
                        '/photo/', '/video/', '/posts/', '/permalink/',
                        '/notifications/', '/messages/',
                        '/memories/', '/onthisday/', '/reel/', '/reels/',
                        '/ad_campaign/', '/ads/', '/settings/', '/help/',
                        '/stories/create', '/composer/',
                        'facebook.com/https:', 'facebook.com/http:',
                    ]
                    
                    # Check if URL contains any excluded patterns
                    if any(ex in url.lower() for ex in excluded_patterns):
                        continue
                    
                    # Extract the path part
                    url_path = url.replace(self.facebook_config.base_url, '').replace('https://www.facebook.com', '').strip('/')
                    
                    # Skip very long URLs or empty paths
                    if len(url_path) > 150 or len(url_path) < 1:
                        continue
                    
                    # Skip URLs that are just query params or fragments
                    if url_path.startswith('?') or url_path.startswith('#'):
                        continue
                    
                    # Skip if already seen
                    if url in seen_urls:
                        continue
                    
                    seen_urls.add(url)

                    # Get display name from link text
                    display_name = ""
                    try:
                        link_text = await link.inner_text()
                        if link_text:
                            # Clean up the text - take first line only
                            lines = [l.strip() for l in link_text.strip().split('\n') if l.strip()]
                            if lines:
                                display_name = lines[0]
                                # Limit length
                                if len(display_name) > 100:
                                    display_name = display_name[:100]
                        
                        # Try aria-label if no text
                        if not display_name or len(display_name) < 2:
                            aria_label = await link.get_attribute('aria-label')
                            if aria_label and 2 < len(aria_label) < 100:
                                display_name = aria_label
                    except:
                        pass

                    # Extract username/ID from URL
                    username = ""
                    if '/profile.php?id=' in url:
                        username = url.split('id=')[1].split('&')[0]
                    elif '/pages/' in url:
                        parts = url.split('/pages/')[1].split('/')
                        if len(parts) >= 2:
                            username = parts[1]  # Use the ID part
                        else:
                            username = parts[0]
                    else:
                        # Extract first path segment
                        parts = url_path.split('/')
                        if parts:
                            username = parts[0].split('?')[0]

                    # Validate username
                    if not username or len(username) < 2:
                        continue
                    
                    # Skip common navigation/UI items
                    skip_items = [
                        'home', 'menu', 'notifications', 'messages', 'friends', 
                        'watch', 'marketplace', 'groups', 'gaming', 
                        'stories', 'story', 'create', 'composer',
                        'timeline', 'about', 'photos', 'videos',
                    ]
                    if username.lower() in skip_items:
                        continue
                    
                    # Skip generic display names
                    if display_name:
                        generic_names = [
                            'see all', 'show more', 'show less', 'close', 'open',
                            'menu', 'more', 'less', 'next', 'previous', 'back',
                            'create story', 'share a photo', 'write something',
                            'timeline', 'photos', 'videos', 'about'
                        ]
                        if display_name.lower() in generic_names or 'timeline' in display_name.lower():
                            continue

                    # Must have either a good display name or valid username
                    if not display_name or len(display_name) < 2:
                        display_name = username

                    # Check for verification badge
                    is_verified = False
                    try:
                        # Facebook verification badges can appear as:
                        # - SVG with aria-label="Verified"
                        # - Image with alt="Verified"
                        # - Specific data attributes
                        parent = await link.evaluate_handle("el => el.closest('div')")
                        
                        verification_selectors = [
                            "svg[aria-label='Verified']",
                            "img[alt='Verified']",
                            "i[data-visualcompletion='css-img'][style*='verified']",
                            "[aria-label*='Verified']"
                        ]
                        
                        for selector in verification_selectors:
                            badge = await parent.query_selector(selector)
                            if badge:
                                is_verified = True
                                break
                    except:
                        pass

                    # Detect suspicious patterns (fake verification claims)
                    suspicious_patterns = self._detect_suspicious_patterns(username, display_name, is_verified)

                    account = {
                        'username': username,
                        'display_name': display_name,
                        'url': url,
                        'is_verified': is_verified,
                        'suspicious_patterns': suspicious_patterns,
                        'risk_level': self._calculate_risk_level(is_verified, suspicious_patterns),
                        'found_at': datetime.now().isoformat()
                    }

                    accounts.append(account)
                    
                    # Display with risk indicators
                    if is_verified:
                        status = "✓ VERIFIED"
                    elif suspicious_patterns:
                        status = f"🚨 HIGH RISK ({', '.join(suspicious_patterns)})"
                    else:
                        status = "⚠ UNVERIFIED"
                    
                    print(f"   Found: {display_name} [{status}]")

                except Exception as e:
                    continue

            return accounts

        except Exception as e:
            print(f"Error extracting accounts: {e}")
            return []
    
    def _save_to_json(self, accounts: List[dict], output_file: str, search_term: str):
        """Save accounts to JSON file organized by CSE name with similarity filtering"""
        try:
            from utils.similarity import filter_accounts_by_similarity
            
            # Apply similarity filter
            # Keep accounts with similarity between 0.3 and 1.0
            # This filters out accounts that are too different from the search term
            filtered_accounts = filter_accounts_by_similarity(
                accounts, 
                search_term, 
                min_similarity=0.3,
                max_similarity=1.0
            )
            
            print(f"   Filtered: {len(accounts)} -> {len(filtered_accounts)} accounts (similarity >= 0.3)")
            
            # Load existing data if file exists
            existing_data = {}
            if os.path.exists(output_file):
                try:
                    with open(output_file, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                except:
                    existing_data = {}
            
            # Add or update the CSE entry
            existing_data[search_term] = {
                'timestamp': datetime.now().isoformat(),
                'total_accounts': len(filtered_accounts),
                'accounts': filtered_accounts
            }
            
            # Save back to file
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Results saved to {output_file}")
            
        except Exception as e:
            print(f"Error saving to JSON: {e}")
    
    async def close(self):
        """Close browser resources"""
        if self._context:
            await self._context.close()

    def _detect_suspicious_patterns(self, username: str, display_name: str, is_verified: bool) -> List[str]:
        """
        Detect suspicious patterns in username/display name that indicate fake verification
        Returns list of detected patterns
        """
        if is_verified:
            return []  # Actually verified, no suspicious patterns
        
        patterns = []
        username_lower = username.lower()
        display_name_lower = display_name.lower()
        
        # Check for fake verification claims
        verification_keywords = ['verified', 'official', 'authentic', 'real', 'genuine', 'legit']
        for keyword in verification_keywords:
            if keyword in username_lower:
                patterns.append(f"'{keyword}' in username")
            elif keyword in display_name_lower and keyword not in username_lower:
                patterns.append(f"'{keyword}' in display name")
        
        # Check for common phishing patterns
        if '_official' in username_lower or 'official_' in username_lower or 'official.' in username_lower:
            patterns.append("'official' prefix/suffix")
        
        if username_lower.endswith('_verified') or username_lower.startswith('verified_'):
            patterns.append("'verified' prefix/suffix")
        
        # Check for multiple dots/underscores (common in fake accounts)
        if username.count('.') >= 3 or username.count('_') >= 3:
            patterns.append("multiple special chars")
        
        # Check for numbers at the end (common in impersonation)
        if len(username) > 2 and username[-1].isdigit() and username[-2:].isdigit():
            patterns.append("trailing numbers")
        
        # Check for special character combinations
        if '..' in username or '__' in username:
            patterns.append("repeated special chars")
        
        return patterns
    
    def _calculate_risk_level(self, is_verified: bool, suspicious_patterns: List[str]) -> str:
        """
        Calculate risk level based on verification status and suspicious patterns
        Returns: 'low', 'medium', 'high', or 'critical'
        """
        if is_verified:
            return 'low'  # Verified accounts are low risk
        
        if not suspicious_patterns:
            return 'medium'  # Unverified but no suspicious patterns
        
        # High risk if has suspicious patterns
        critical_keywords = ["'verified'", "'official'", "'authentic'"]
        has_critical = any(any(kw in pattern for kw in critical_keywords) for pattern in suspicious_patterns)
        
        if has_critical or len(suspicious_patterns) >= 3:
            return 'critical'  # Multiple red flags or critical keywords
        
        return 'high'  # Some suspicious patterns
