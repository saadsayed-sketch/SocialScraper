"""
Simplified X (Twitter) scraper focused on account detection for phishing analysis
"""
import asyncio
import json
import os
import re
from datetime import datetime
from typing import List, Optional, Dict, Any
from playwright.async_api import Page, ElementHandle

from core.models import CSEProfile
from core.browser import BrowserManager
from core.config import XConfig


class XScraper:
    """Simplified X (Twitter) scraper for account detection"""
    
    def __init__(self, browser_manager: BrowserManager, x_config: XConfig):
        self.browser_manager = browser_manager
        self.x_config = x_config
        self._page: Optional[Page] = None
        self._context = None
        self._url_regex = re.compile(r'https?://[^\s<>"{}|\\^`[\]]+')
    
    async def initialize(self):
        """Initialize browser context and page"""
        if not self._context:
            self._context = await self.browser_manager.create_context("x")
            self._page = await self.browser_manager.create_page_for_url_extraction(self._context)
    
    async def login_with_session(self) -> bool:
        """Login using saved session from persistent storage"""
        try:
            # Check for persistent session first
            persistent_session_path = "./persistent_sessions/x"
            session_file = "./sessions/x_session.json"
            
            # Try persistent session first (preferred) - use playwright's persistent context with stealth
            if os.path.exists(persistent_session_path) and os.path.isdir(persistent_session_path):
                print("🔄 Loading persistent session with stealth settings...")
                # Check if it has content
                if len(os.listdir(persistent_session_path)) > 0:
                    # Use persistent context directly with enhanced stealth
                    from playwright.async_api import async_playwright
                    import random
                    
                    playwright = await async_playwright().start()
                    
                    # Enhanced stealth arguments
                    browser = await playwright.chromium.launch_persistent_context(
                        user_data_dir=persistent_session_path,
                        headless=self.browser_manager.config.headless,
                        viewport=self.browser_manager.config.viewport,
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
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
                        ]
                    )
                    
                    # Apply stealth scripts to context
                    await browser.add_init_script("""
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined,
                        });
                        
                        delete navigator.__proto__.webdriver;
                        
                        window.chrome = {
                            runtime: {},
                        };
                        
                        Object.defineProperty(navigator, 'plugins', {
                            get: () => [1, 2, 3, 4, 5],
                        });
                        
                        Object.defineProperty(navigator, 'languages', {
                            get: () => ['en-US', 'en'],
                        });
                    """)
                    
                    # Store the context
                    self._context = browser
                    
                    # Get or create page
                    if len(browser.pages) > 0:
                        self._page = browser.pages[0]
                    else:
                        self._page = await browser.new_page()
                    
                    # Test if session is valid
                    await self._page.goto(self.x_config.base_url)
                    await asyncio.sleep(5)  # Wait longer for any challenges
                    
                    if await self._is_logged_in():
                        print("✅ X persistent session loaded successfully with stealth")
                        return True
                    else:
                        print("⚠️  Session loaded but not logged in (bot detected)")
                        await browser.close()
                        await playwright.stop()
            
            # Fallback to JSON session file
            if os.path.exists(session_file):
                print("🔄 Loading session from JSON...")
                self._context = await self.browser_manager.create_context("x", session_path=session_file)
                self._page = await self.browser_manager.create_page_for_url_extraction(self._context)
                
                # Test if session is valid
                await self._page.goto(self.x_config.base_url)
                await asyncio.sleep(3)
                
                if await self._is_logged_in():
                    print("✅ X session loaded successfully")
                    return True
            
            print("❌ No saved session found or session expired.")
            print("   Please login when prompted.")
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
            print("X (Twitter) Manual Login Required")
            print("=" * 60)
            print("\nA browser window will open for you to login.")
            print("Please login manually, then the scraper will continue.")
            print("\n⚠️  DO NOT CLOSE THE BROWSER WINDOW!")
            print("=" * 60)
            
            input("\nPress Enter to open browser for login...")
            
            # Create persistent session directory
            persistent_session_path = "./persistent_sessions/x"
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
            
            # Navigate to X
            print("\n🌐 Opening X (Twitter)...")
            await page.goto(self.x_config.base_url)
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
            
            if await self._is_logged_in_page(page):
                print("✅ Login verified!")
                
                # Save to JSON session as well
                sessions_dir = "./sessions"
                os.makedirs(sessions_dir, exist_ok=True)
                session_file = f"{sessions_dir}/x_session.json"
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
            # Look for home timeline or navigation elements
            home_timeline = await self._page.query_selector('[data-testid="primaryColumn"]')
            return home_timeline is not None
        except:
            return False
    
    async def _is_logged_in_page(self, page: Page) -> bool:
        """Check if logged in on a specific page"""
        try:
            home_timeline = await page.query_selector('[data-testid="primaryColumn"]')
            return home_timeline is not None
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
        print("⚠️  No saved X session found")
        print("=" * 60)
        print("\nYou need to login to X to use the scraper.")
        
        response = input("\nWould you like to login now? (y/n): ").strip().lower()
        
        if response == 'y' or response == 'yes':
            return await self.login_interactive()
        else:
            print("\n❌ Cannot proceed without login.")
            return False
    
    async def search_and_collect_accounts(self, search_term: str, output_file: str = None) -> List[dict]:
        """
        Search for accounts and collect them
        
        Args:
            search_term: Term to search for
            output_file: JSON file to save results (optional)
            
        Returns:
            List of account dictionaries with username and URL
        """
        try:
            if not self._page:
                print("❌ Not initialized. Please login first.")
                return []
            
            print(f"🔍 Searching for: {search_term}")
            
            # Navigate to search with people filter
            search_url = f"{self.x_config.base_url}/search?q={search_term}&src=typed_query&f=user"
            print(f"   Navigating to: {search_url}")
            await self._page.goto(search_url)
            await asyncio.sleep(5)  # Increased wait time
            
            # Check current URL
            current_url = self._page.url
            print(f"   Current URL: {current_url}")
            
            # Extract accounts from search results
            accounts = await self._extract_accounts_from_search_results()
            
            # Filter out false positives (suggested accounts)
            filtered_accounts = self._filter_relevant_accounts(accounts, search_term)
            
            if len(accounts) > 0 and len(filtered_accounts) == 0:
                print(f"   ⚠️  Bot detection suspected: All {len(accounts)} accounts filtered as irrelevant")
                print(f"   💡 Tip: Add longer delays between searches or reduce batch size")
            
            print(f"✅ Found {len(filtered_accounts)} relevant accounts (filtered {len(accounts) - len(filtered_accounts)} false positives)")
            
            # Save to JSON if output file specified
            if output_file:
                self._save_to_json(filtered_accounts, output_file, search_term)
            
            return filtered_accounts
            
        except Exception as e:
            print(f"❌ Search error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _filter_relevant_accounts(self, accounts: List[dict], search_term: str) -> List[dict]:
        """
        Filter out false positives (suggested accounts) that are unrelated to search term
        
        Common false positives when X detects bot activity:
        - Celebrity accounts (Obama, Tesla, Musk, etc.)
        - Generic popular accounts (NatGeo, CNN, etc.)
        - Sports personalities
        """
        # Known false positive accounts (suggested accounts)
        false_positive_usernames = {
            'barackobama', 'elonmusk', 'tesla', 'natgeo', 'cnnbrk', 'cnn',
            'sachin_rt', 'imvkohli', 'isro', 'narendramodi', 'pmo india',
            'billgates', 'jeffbezos', 'markzuckerberg', 'sundarpichai',
            'tim_cook', 'satyanadella', 'jack', 'bts_official', 'cristiano',
            'leomessi', 'neymarjr', 'kingjames', 'kanyewest', 'taylorswift13',
            'katyperry', 'rihanna', 'justinbieber', 'arianagrande', 'selenagomez'
        }
        
        search_term_lower = search_term.lower()
        search_words = set(search_term_lower.split())
        
        filtered = []
        for account in accounts:
            username_lower = account.get('username', '').lower()
            display_name_lower = account.get('display_name', '').lower()
            bio_lower = account.get('bio_description', '').lower()
            
            # Skip known false positives
            if username_lower in false_positive_usernames:
                print(f"   🚫 Filtered false positive: @{account['username']} (suggested account)")
                continue
            
            # Check if account is relevant to search term
            # Account is relevant if:
            # 1. Username contains any search word
            # 2. Display name contains any search word
            # 3. Bio contains any search word
            is_relevant = False
            
            for word in search_words:
                if len(word) > 2:  # Skip very short words
                    if (word in username_lower or 
                        word in display_name_lower or 
                        word in bio_lower):
                        is_relevant = True
                        break
            
            if is_relevant:
                filtered.append(account)
            else:
                print(f"   🚫 Filtered irrelevant: @{account['username']} (no match with '{search_term}')")
        
        return filtered
    
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

    
    async def _extract_accounts_from_search_results(self) -> List[dict]:
        """Extract account information from X search results"""
        try:
            accounts = []
            seen_usernames = set()
            
            # Wait for results to load
            print(f"   Waiting for search results...")
            try:
                await self._page.wait_for_selector('[data-testid="UserCell"]', timeout=10000)
                user_cells = await self._page.query_selector_all('[data-testid="UserCell"]')
                print(f"   Found {len(user_cells)} UserCell elements")
            except Exception as e:
                print(f"   ⚠️  No UserCell elements found, trying alternative selectors...")
                # Try alternative selectors
                user_cells = await self._page.query_selector_all('[data-testid="User-Name"]')
                if not user_cells:
                    user_cells = await self._page.query_selector_all('article[data-testid="tweet"]')
                print(f"   Found {len(user_cells)} elements with alternative selector")
            
            if not user_cells:
                print(f"   ⚠️  No account elements found on page")
                # Save screenshot for debugging
                try:
                    await self._page.screenshot(path='x_search_debug.png')
                    print(f"   📸 Screenshot saved to x_search_debug.png")
                except:
                    pass
                return []
            
            for cell in user_cells[:10]:  # Limit to first 10
                try:
                    account = await self._extract_account_from_user_cell(cell)
                    if account and account['username'] not in seen_usernames:
                        seen_usernames.add(account['username'])
                        accounts.append(account)
                        
                        # Display with risk indicators
                        if account.get('is_verified'):
                            verification_type = account.get('verification_type', 'blue')
                            status = f"✓ VERIFIED ({verification_type})"
                        elif account.get('suspicious_patterns'):
                            patterns = account['suspicious_patterns']
                            status = f"🚨 HIGH RISK ({', '.join(patterns[:2])})"  # Show first 2 patterns
                        else:
                            status = "⚠ UNVERIFIED"
                        
                        print(f"   Found: @{account['username']} [{status}]")
                except Exception as e:
                    print(f"   ⚠️  Error extracting account: {e}")
                    continue
            
            return accounts
            
        except Exception as e:
            print(f"   ❌ Failed to extract accounts from X search results: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def _extract_account_from_user_cell(self, cell: ElementHandle) -> Optional[Dict[str, Any]]:
        """Extract account information from a user cell element"""
        try:
            # Try multiple selector strategies
            username = None
            display_name = None
            profile_url = None
            
            # Strategy 1: Look for any link that starts with /
            links = await cell.query_selector_all('a[href^="/"]')
            for link in links:
                href = await link.get_attribute('href')
                if href and href.startswith('/') and not href.startswith('/i/') and not href.startswith('/search'):
                    # Extract username from href
                    parts = href.strip('/').split('/')
                    if parts and parts[0]:
                        username = parts[0]
                        profile_url = f"{self.x_config.base_url}/{username}"
                        break
            
            if not username:
                return None
            
            # Try to get display name and bio from cell text
            cell_text = await cell.text_content()
            display_name = username  # Default
            bio_description = ""
            
            if cell_text:
                # Split into lines and clean
                lines = [line.strip() for line in cell_text.strip().split('\n') if line.strip()]
                
                # Filter out noise
                clean_lines = []
                for line in lines:
                    # Skip these patterns
                    if any(skip in line for skip in ['Follow', 'Click to', '@' + username, username]):
                        continue
                    clean_lines.append(line)
                
                # First clean line is display name, rest is bio
                if clean_lines:
                    display_name = clean_lines[0]
                    if len(clean_lines) > 1:
                        bio_description = ' '.join(clean_lines[1:])
            
            # Check for verification badge
            is_verified = False
            verification_type = None
            try:
                # X (Twitter) has multiple verification types:
                # - Blue checkmark (X Premium/Twitter Blue)
                # - Gold checkmark (Organizations)
                # - Gray checkmark (Government/Multilateral)
                # Look for verification badge SVGs
                verification_selectors = [
                    "svg[aria-label*='Verified']",
                    "svg[data-testid='icon-verified']",
                    "[aria-label*='Verified account']",
                    "svg path[d*='M22.25']"  # Common path for verification badge
                ]
                
                for selector in verification_selectors:
                    badge = await cell.query_selector(selector)
                    if badge:
                        is_verified = True
                        # Try to determine verification type from aria-label
                        aria_label = await badge.get_attribute('aria-label')
                        if aria_label:
                            if 'government' in aria_label.lower():
                                verification_type = 'government'
                            elif 'business' in aria_label.lower() or 'organization' in aria_label.lower():
                                verification_type = 'organization'
                            else:
                                verification_type = 'blue'
                        break
            except:
                pass
            
            # Detect suspicious patterns (fake verification claims)
            suspicious_patterns = self._detect_suspicious_patterns(username, display_name, bio_description, is_verified)
            
            return {
                'username': username,
                'display_name': display_name,
                'url': profile_url,
                'bio_description': bio_description,
                'is_verified': is_verified,
                'verification_type': verification_type,
                'suspicious_patterns': suspicious_patterns,
                'risk_level': self._calculate_risk_level(is_verified, suspicious_patterns),
                'found_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"      ⚠️  Error in _extract_account_from_user_cell: {e}")
            return None


    def _detect_suspicious_patterns(self, username: str, display_name: str, bio: str, is_verified: bool) -> List[str]:
        """
        Detect suspicious patterns in username/display name/bio that indicate fake verification
        Returns list of detected patterns
        """
        if is_verified:
            return []  # Actually verified, no suspicious patterns
        
        patterns = []
        username_lower = username.lower()
        display_name_lower = display_name.lower()
        bio_lower = bio.lower()
        
        # Check for fake verification claims
        verification_keywords = ['verified', 'official', 'authentic', 'real', 'genuine', 'legit']
        for keyword in verification_keywords:
            if keyword in username_lower:
                patterns.append(f"'{keyword}' in username")
            elif keyword in display_name_lower and keyword not in username_lower:
                patterns.append(f"'{keyword}' in display name")
            elif keyword in bio_lower and keyword not in username_lower and keyword not in display_name_lower:
                patterns.append(f"'{keyword}' in bio")
        
        # Check for common phishing patterns
        if '_official' in username_lower or 'official_' in username_lower:
            patterns.append("'official' prefix/suffix")
        
        if username_lower.endswith('_verified') or username_lower.startswith('verified_'):
            patterns.append("'verified' prefix/suffix")
        
        # Check for multiple underscores (common in fake accounts)
        if username.count('_') >= 3:
            patterns.append("multiple underscores")
        
        # Check for numbers at the end (common in impersonation)
        if len(username) > 2 and username[-1].isdigit() and username[-2:].isdigit():
            patterns.append("trailing numbers")
        
        # Check for special character combinations
        if '__' in username:
            patterns.append("repeated underscores")
        
        # Check for suspicious bio claims
        if 'official account' in bio_lower or 'verified account' in bio_lower:
            patterns.append("verification claim in bio")
        
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
