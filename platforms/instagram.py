"""
Instagram scraper - Basic account search and URL collection
"""
import asyncio
import json
import os
from datetime import datetime
from typing import List, Optional
from playwright.async_api import Page

from core.browser import BrowserManager
from core.config import InstagramConfig


class InstagramScraper:
    """Basic Instagram scraper for searching accounts and collecting URLs"""
    
    def __init__(self, browser_manager: BrowserManager, instagram_config: InstagramConfig):
        self.browser_manager = browser_manager
        self.instagram_config = instagram_config
        self._page: Optional[Page] = None
        self._context = None
    
    async def initialize(self):
        """Initialize browser context and page"""
        if not self._context:
            self._context = await self.browser_manager.create_context("instagram")
            self._page = await self.browser_manager.create_page_for_url_extraction(self._context)
    
    async def login_with_session(self) -> bool:
        """Login using saved session from persistent storage"""
        try:
            # Check for persistent session first
            persistent_session_path = "./persistent_sessions/instagram"
            session_file = "./sessions/instagram_session.json"
            
            # Try persistent session first (preferred)
            if os.path.exists(persistent_session_path) and os.path.isdir(persistent_session_path):
                print("🔄 Loading persistent session...")
                # Check if it has content
                if len(os.listdir(persistent_session_path)) > 0:
                    self._context = await self.browser_manager.create_context("instagram", session_path=session_file)
                    self._page = await self.browser_manager.create_page_for_url_extraction(self._context)
                    
                    # Test if session is valid
                    await self._page.goto(self.instagram_config.base_url)
                    await asyncio.sleep(3)
                    
                    if await self._is_logged_in():
                        print("✅ Instagram persistent session loaded successfully")
                        return True
            
            # Fallback to JSON session file
            if os.path.exists(session_file):
                print("🔄 Loading session from JSON...")
                self._context = await self.browser_manager.create_context("instagram", session_path=session_file)
                self._page = await self.browser_manager.create_page_for_url_extraction(self._context)
                
                # Test if session is valid
                await self._page.goto(self.instagram_config.base_url)
                await asyncio.sleep(3)
                
                if await self._is_logged_in():
                    print("✅ Instagram session loaded successfully")
                    return True
            
            print("❌ No saved session found.")
            print("   Please run: python instagram_manual_login.py")
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
            print("Instagram Manual Login Required")
            print("=" * 60)
            print("\nA browser window will open for you to login.")
            print("Please login manually, then the scraper will continue.")
            print("\n⚠️  DO NOT CLOSE THE BROWSER WINDOW!")
            print("=" * 60)
            
            input("\nPress Enter to open browser for login...")
            
            # Create persistent session directory
            persistent_session_path = "./persistent_sessions/instagram"
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
            
            # Navigate to Instagram
            print("\n🌐 Opening Instagram...")
            await page.goto(self.instagram_config.base_url)
            await asyncio.sleep(3)
            
            print("\n" + "=" * 60)
            print("✋ PLEASE LOGIN IN THE BROWSER")
            print("=" * 60)
            print("\nSteps:")
            print("1. Enter your username and password")
            print("2. Complete any 2FA or verification")
            print("3. Wait until you see your home feed")
            print("4. Come back here and press Enter")
            print("\n⚠️  DO NOT CLOSE THE BROWSER!")
            print("=" * 60)
            
            input("\nPress Enter after you've logged in...")
            
            # Verify login
            print("\n🔍 Verifying login...")
            await asyncio.sleep(2)
            
            home_icon = await page.query_selector("svg[aria-label='Home']")
            
            if home_icon:
                print("✅ Login verified!")
                
                # Save to JSON session as well
                sessions_dir = "./sessions"
                os.makedirs(sessions_dir, exist_ok=True)
                session_file = f"{sessions_dir}/instagram_session.json"
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
        try:
            # Look for home icon or navigation elements
            home_icon = await self._page.query_selector("svg[aria-label='Home']")
            return home_icon is not None
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
        print("⚠️  No saved Instagram session found")
        print("=" * 60)
        print("\nYou need to login to Instagram to use the scraper.")
        
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
            
            # Go to Instagram home first
            await self._page.goto(f"{self.instagram_config.base_url}/")
            await asyncio.sleep(2)
            
            # Click on Search icon in left navigation (4th icon)
            # Try multiple selectors for the search icon
            search_icon_clicked = False
            search_icon_selectors = [
                "svg[aria-label='Search']",
                "a[href='#'][role='link'] svg[aria-label='Search']",
                "span:has-text('Search')",
                "[aria-label='Search']"
            ]
            
            for selector in search_icon_selectors:
                try:
                    search_icon = await self._page.query_selector(selector)
                    if search_icon:
                        # Click the parent link/button
                        parent = await search_icon.evaluate_handle("el => el.closest('a, div[role=\"button\"]')")
                        await parent.click()
                        search_icon_clicked = True
                        print("   Clicked Search icon")
                        await asyncio.sleep(2)
                        break
                except:
                    continue
            
            if not search_icon_clicked:
                print("   ⚠️ Could not find Search icon, trying search box directly")
            
            # Find and click on search input box
            search_box = await self._page.wait_for_selector("input[placeholder*='Search']", timeout=10000)
            await search_box.click()
            await asyncio.sleep(1)
            
            # Type search query
            await search_box.fill(cse_name)
            await asyncio.sleep(3)  # Wait for search results to appear
            
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
        """Extract account URLs from search results (top area only)"""
        try:
            accounts = []
            seen_usernames = set()

            # Wait for search results container
            await asyncio.sleep(2)

            print("   Looking for search results panel...")

            # Try to find the search results panel
            search_panel = None
            search_panel_selectors = [
                "div[role='dialog']",  # Search results dialog
                "div[role='menu']",     # Search results menu
            ]

            for selector in search_panel_selectors:
                try:
                    panel = await self._page.query_selector(selector)
                    if panel:
                        test_links = await panel.query_selector_all("a[href^='/']")
                        if len(test_links) > 0:
                            search_panel = panel
                            print(f"   ✓ Found search panel with {len(test_links)} links")
                            break
                except:
                    continue

            # Extract links from panel or use position-based filtering
            if search_panel:
                links = await search_panel.query_selector_all("a[href^='/']")
                print(f"   Extracting from search panel...")
            else:
                print("   ⚠️  Search panel not found, using position-based filtering")
                all_links = await self._page.query_selector_all("a[href^='/']")

                # Filter by position: top-left area only (excludes posts below and sidebar)
                links = []
                for link in all_links:
                    try:
                        box = await link.bounding_box()
                        if box:
                            # Search results: left side (x < 700) AND top area (y < 500)
                            if box['x'] < 700 and box['y'] < 500:
                                links.append(link)
                    except:
                        continue

                print(f"   Found {len(links)} links in search area")

            # Limit to first 10 to avoid feed posts
            links = links[:10]

            # Extract accounts
            for link in links:
                try:
                    href = await link.get_attribute('href')
                    if not href:
                        continue

                    username = href.strip('/').split('/')[0]

                    # Filter out non-account URLs
                    excluded = ['explore', 'p', 'reel', 'reels', 'tv', 'stories', 'direct', 
                               'accounts', 'about', 'help', 'press', 'api', 'jobs', 'privacy', 
                               'terms', 'locations', 'language', 'meta', 'verified', 'shop',
                               'hashtag', 'tags']

                    if (username and 
                        username not in excluded and 
                        username not in seen_usernames and
                        len(username) > 2 and
                        username.replace('_', '').replace('.', '').isalnum()):

                        seen_usernames.add(username)

                        # Get display name and verification status
                        display_name = username
                        is_verified = False
                        try:
                            parent = await link.evaluate_handle("el => el.closest('div')")
                            text_content = await parent.evaluate("el => el.textContent")
                            if text_content and text_content.strip():
                                lines = text_content.strip().split('\n')
                                if lines and lines[0] != username and not lines[0].startswith('@'):
                                    display_name = lines[0]
                            
                            # Check for verification badge (blue checkmark)
                            # Instagram uses svg with aria-label="Verified" or specific title
                            verification_selectors = [
                                "svg[aria-label='Verified']",
                                "svg[title='Verified']",
                                "span[title='Verified']"
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
                            'url': f"{self.instagram_config.base_url}/{username}/",
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
                        
                        print(f"   Found: @{username} [{status}]")

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
        
        # Check for fake verification claims in username
        verification_keywords = ['verified', 'official', 'authentic', 'real', 'genuine', 'legit']
        for keyword in verification_keywords:
            if keyword in username_lower:
                patterns.append(f"'{keyword}' in username")
            elif keyword in display_name_lower and keyword not in username_lower:
                patterns.append(f"'{keyword}' in display name")
        
        # Check for common phishing patterns
        if '_official' in username_lower or 'official_' in username_lower:
            patterns.append("'official' prefix/suffix")
        
        if username_lower.endswith('_verified') or username_lower.startswith('verified_'):
            patterns.append("'verified' prefix/suffix")
        
        # Check for multiple underscores (common in fake accounts)
        if username.count('_') >= 3:
            patterns.append("multiple underscores")
        
        # Check for numbers at the end (common in impersonation)
        if username[-1].isdigit() and username[-2:].isdigit():
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
