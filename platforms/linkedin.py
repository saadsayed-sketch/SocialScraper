"""
LinkedIn scraper - Company search and URL collection
"""
import asyncio
import json
import os
from datetime import datetime
from typing import List, Optional
from playwright.async_api import Page

from core.browser import BrowserManager
from core.config import LinkedinConfig


class LinkedinScraper:
    """LinkedIn scraper for searching companies and collecting URLs"""
    
    def __init__(self, browser_manager: BrowserManager, linkedin_config: LinkedinConfig):
        self.browser_manager = browser_manager
        self.linkedin_config = linkedin_config
        self._page: Optional[Page] = None
        self._context = None
    
    async def initialize(self):
        """Initialize browser context and page"""
        if not self._context:
            self._context = await self.browser_manager.create_context("linkedin")
            self._page = await self.browser_manager.create_page_for_url_extraction(self._context)
    
    async def login_with_session(self) -> bool:
        """Login using saved session from persistent storage"""
        try:
            # Check for persistent session first
            persistent_session_path = "./persistent_sessions/linkedin"
            session_file = "./sessions/linkedin_session.json"
            
            # Try persistent session first (preferred)
            if os.path.exists(persistent_session_path) and os.path.isdir(persistent_session_path):
                print("🔄 Loading persistent session...")
                # Check if it has content
                if len(os.listdir(persistent_session_path)) > 0:
                    self._context = await self.browser_manager.create_context("linkedin", session_path=session_file)
                    self._page = await self.browser_manager.create_page_for_url_extraction(self._context)
                    
                    # Test if session is valid - go to feed page
                    print("   Testing session validity...")
                    await self._page.goto(f"{self.linkedin_config.base_url}/feed/")
                    await asyncio.sleep(5)  # Give more time for LinkedIn to load
                    
                    # Debug: print current URL
                    current_url = self._page.url
                    print(f"   Current URL: {current_url}")
                    
                    if await self._is_logged_in():
                        print("✅ LinkedIn persistent session loaded successfully")
                        return True
                    else:
                        print("   ⚠️  Session expired or invalid")
            
            # Fallback to JSON session file
            if os.path.exists(session_file):
                print("🔄 Loading session from JSON...")
                self._context = await self.browser_manager.create_context("linkedin", session_path=session_file)
                self._page = await self.browser_manager.create_page_for_url_extraction(self._context)
                
                # Test if session is valid - go to feed page
                print("   Testing session validity...")
                await self._page.goto(f"{self.linkedin_config.base_url}/feed/")
                await asyncio.sleep(5)  # Give more time for LinkedIn to load
                
                # Debug: print current URL
                current_url = self._page.url
                print(f"   Current URL: {current_url}")
                
                if await self._is_logged_in():
                    print("✅ LinkedIn session loaded successfully")
                    return True
                else:
                    print("   ⚠️  Session expired or invalid")
            
            print("❌ No saved session found.")
            print("   Please run: python linkedin_manual_login.py")
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
            print("LinkedIn Manual Login Required")
            print("=" * 60)
            print("\nA browser window will open for you to login.")
            print("Please login manually, then the scraper will continue.")
            print("\n⚠️  DO NOT CLOSE THE BROWSER WINDOW!")
            print("=" * 60)
            
            input("\nPress Enter to open browser for login...")
            
            # Create persistent session directory
            persistent_session_path = "./persistent_sessions/linkedin"
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
            
            # Navigate to LinkedIn
            print("\n🌐 Opening LinkedIn...")
            await page.goto(self.linkedin_config.base_url)
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
            await asyncio.sleep(3)
            
            # Try to navigate to feed to verify login
            print("   Navigating to feed page...")
            await page.goto(f"{self.linkedin_config.base_url}/feed/")
            await asyncio.sleep(5)  # Give LinkedIn more time to load
            
            # Check current URL
            current_url = page.url
            print(f"   Current URL: {current_url}")
            
            # LinkedIn uses different selectors - check multiple elements
            logged_in = False
            
            # Check 1: URL check (most reliable)
            if '/feed/' in current_url and '/login' not in current_url:
                print("   ✓ On feed page (not login page)")
                logged_in = True
            
            # Check 2: Look for any navigation element
            if not logged_in:
                nav_elements = await page.query_selector_all("nav")
                if len(nav_elements) > 0:
                    print(f"   ✓ Found {len(nav_elements)} navigation element(s)")
                    logged_in = True
            
            # Check 3: Check for feed link
            if not logged_in:
                feed_link = await page.query_selector("a[href*='/feed/']")
                if feed_link:
                    print("   ✓ Found feed link")
                    logged_in = True
            
            # Check 4: Check for global nav
            if not logged_in:
                global_nav = await page.query_selector(".global-nav, [class*='global-nav']")
                if global_nav:
                    print("   ✓ Found global nav")
                    logged_in = True
            
            # Check 5: Check for search box
            if not logged_in:
                search_box = await page.query_selector("input[placeholder*='Search'], input[aria-label*='Search']")
                if search_box:
                    print("   ✓ Found search box")
                    logged_in = True
            
            # Check 6: Look for any profile/user elements
            if not logged_in:
                profile_elements = await page.query_selector_all("img[alt*='profile'], img[alt*='Photo']")
                if len(profile_elements) > 0:
                    print(f"   ✓ Found {len(profile_elements)} profile image(s)")
                    logged_in = True
            
            if not logged_in:
                print("   ✗ No login indicators found")
                print("   Tip: Make sure you're fully logged in and can see your feed")
            
            if logged_in:
                print("✅ Login verified!")
                
                # Save to JSON session as well
                sessions_dir = "./sessions"
                os.makedirs(sessions_dir, exist_ok=True)
                session_file = f"{sessions_dir}/linkedin_session.json"
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
            # LinkedIn-specific login detection - try multiple selectors
            print("   Checking login status...")
            
            # Check 1: URL check (most reliable)
            current_url = self._page.url
            if '/feed/' in current_url and '/login' not in current_url:
                print(f"   ✓ On feed page (URL: {current_url})")
                return True
            
            # Check 2: Look for any navigation element
            nav_elements = await self._page.query_selector_all("nav")
            if len(nav_elements) > 0:
                print(f"   ✓ Found {len(nav_elements)} navigation element(s)")
                return True
            
            # Check 3: Check for feed link in navigation
            feed_link = await self._page.query_selector("a[href*='/feed/']")
            if feed_link:
                print("   ✓ Found feed link")
                return True
            
            # Check 4: Check for global nav (appears when logged in)
            global_nav = await self._page.query_selector(".global-nav, [class*='global-nav']")
            if global_nav:
                print("   ✓ Found global nav")
                return True
            
            # Check 5: Check for search box (only visible when logged in)
            search_box = await self._page.query_selector("input[placeholder*='Search'], input[aria-label*='Search']")
            if search_box:
                print("   ✓ Found search box")
                return True
            
            # Check 6: Check for profile/me link
            profile_link = await self._page.query_selector("a[href*='/in/']")
            if profile_link:
                print("   ✓ Found profile link")
                return True
            
            # Check 7: Look for profile images
            profile_elements = await self._page.query_selector_all("img[alt*='profile'], img[alt*='Photo']")
            if len(profile_elements) > 0:
                print(f"   ✓ Found {len(profile_elements)} profile image(s)")
                return True
            
            print("   ✗ No login indicators found")
            return False
        except Exception as e:
            print(f"   ✗ Error checking login: {e}")
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
        print("⚠️  No saved LinkedIn session found")
        print("=" * 60)
        print("\nYou need to login to LinkedIn to use the scraper.")
        
        response = input("\nWould you like to login now? (y/n): ").strip().lower()
        
        if response == 'y' or response == 'yes':
            return await self.login_interactive()
        else:
            print("\n❌ Cannot proceed without login.")
            return False
    
    async def search_and_collect_accounts(self, cse_name: str, output_file: str = None) -> List[dict]:
        """
        Search for company name and collect company URLs
        
        Args:
            cse_name: Company name to search for
            output_file: JSON file to save results (optional)
            
        Returns:
            List of company dictionaries with name and URL
        """
        try:
            if not self._page:
                print("❌ Not initialized. Please login first.")
                return []
            
            print(f"🔍 Searching for: {cse_name}")
            
            # Go to LinkedIn search with companies filter
            search_url = f"{self.linkedin_config.base_url}/search/results/companies/?keywords={cse_name.replace(' ', '%20')}"
            print(f"   Navigating to: {search_url}")
            await self._page.goto(search_url)
            await asyncio.sleep(5)  # Wait for results to load
            
            # Collect company URLs from search results
            companies = await self._extract_company_urls_from_search()
            
            print(f"✅ Found {len(companies)} compan{'y' if len(companies) == 1 else 'ies'}")
            
            # Save to JSON if output file specified
            if output_file:
                self._save_to_json(companies, output_file, cse_name)
            
            return companies
            
        except Exception as e:
            print(f"Search error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def _extract_company_urls_from_search(self) -> List[dict]:
        """Extract company URLs from LinkedIn company search results"""
        try:
            companies = []
            seen_companies = set()

            # Wait for search results to load
            await asyncio.sleep(3)

            print("   Looking for company results...")

            # LinkedIn company search results use specific selectors
            # Try to find company result containers
            company_containers = await self._page.query_selector_all(
                ".entity-result, .reusable-search__result-container, [data-chameleon-result-urn]"
            )
            
            print(f"   Found {len(company_containers)} result container(s)")

            for container in company_containers[:20]:  # Limit to first 20 results
                try:
                    # Look for company links within the container
                    # LinkedIn company URLs follow pattern: /company/{company-name}/
                    links = await container.query_selector_all("a[href*='/company/']")
                    
                    for link in links:
                        href = await link.get_attribute('href')
                        if not href or '/company/' not in href:
                            continue
                        
                        # Extract company identifier from URL
                        # Format: /company/{company-id}/ or /company/{company-id}
                        parts = href.split('/company/')
                        if len(parts) < 2:
                            continue
                        
                        company_id = parts[1].strip('/').split('/')[0].split('?')[0]
                        
                        if company_id and company_id not in seen_companies:
                            seen_companies.add(company_id)
                            
                            # Try to get company name from the link text or nearby elements
                            company_name = company_id
                            try:
                                # Try to get text from the link
                                link_text = await link.inner_text()
                                if link_text and link_text.strip():
                                    company_name = link_text.strip()
                                else:
                                    # Try to find company name in parent container
                                    name_element = await container.query_selector(
                                        ".entity-result__title-text, .app-aware-link, [aria-label]"
                                    )
                                    if name_element:
                                        name_text = await name_element.inner_text()
                                        if name_text and name_text.strip():
                                            company_name = name_text.strip().split('\n')[0]
                            except:
                                pass
                            
                            company = {
                                'company_id': company_id,
                                'company_name': company_name,
                                'url': f"{self.linkedin_config.base_url}/company/{company_id}/",
                                'found_at': datetime.now().isoformat()
                            }
                            
                            companies.append(company)
                            print(f"   Found: {company_name} ({company_id})")
                
                except Exception as e:
                    continue

            return companies

        except Exception as e:
            print(f"Error extracting companies: {e}")
            import traceback
            traceback.print_exc()
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

                        # Get display name
                        display_name = username
                        try:
                            parent = await link.evaluate_handle("el => el.closest('div')")
                            text_content = await parent.evaluate("el => el.textContent")
                            if text_content and text_content.strip():
                                lines = text_content.strip().split('\n')
                                if lines and lines[0] != username and not lines[0].startswith('@'):
                                    display_name = lines[0]
                        except:
                            pass

                        account = {
                            'username': username,
                            'display_name': display_name,
                            'url': f"{self.linkedin_config.base_url}/{username}/",
                            'found_at': datetime.now().isoformat()
                        }

                        accounts.append(account)
                        print(f"   Found: @{username}")

                except Exception as e:
                    continue

            return accounts

        except Exception as e:
            print(f"Error extracting accounts: {e}")
            return []

    
    def _save_to_json(self, items: List[dict], output_file: str, search_term: str):
        """Save companies/accounts to JSON file organized by search term"""
        try:
            # Determine if we're saving companies or accounts
            item_type = 'companies' if items and 'company_id' in items[0] else 'accounts'
            
            print(f"   Saving {len(items)} {item_type}...")
            
            # Load existing data if file exists
            existing_data = {}
            if os.path.exists(output_file):
                try:
                    with open(output_file, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                except:
                    existing_data = {}
            
            # Add or update the search term entry
            existing_data[search_term] = {
                'timestamp': datetime.now().isoformat(),
                f'total_{item_type}': len(items),
                item_type: items
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
