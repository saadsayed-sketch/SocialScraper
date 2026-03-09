"""
Simplified Reddit platform module for account detection and phishing analysis
"""
import asyncio
import re
from datetime import datetime
from typing import List, Optional, Dict, Any
from playwright.async_api import Page, ElementHandle

from core.models import CSEProfile
from core.browser import BrowserManager
from core.config import RedditConfig
from .base import BasePlatformModule


class RedditScraper(BasePlatformModule):
    """Simplified Reddit platform module for account detection"""
    
    def __init__(self, browser_manager: BrowserManager, reddit_config: RedditConfig):
        super().__init__(browser_manager, reddit_config)
        self.reddit_config = reddit_config
        self._url_regex = re.compile(r'https?://[^\s<>"{}|\\^`[\]]+')
    
    def _get_platform_name(self) -> str:
        """Return the platform name"""
        return "reddit"
    
    async def login(self, username: str, password: str) -> bool:
        """
        Login to Reddit - Manual authentication required
        """
        print("Manual login required. Please log in through the browser window.")
        return False
    
    async def search_accounts(self, search_terms: List[str]) -> List[Dict[str, Any]]:
        """
        Search for Reddit accounts and communities using the provided search terms
        
        Args:
            search_terms: List of terms to search for
            
        Returns:
            List of account/community dictionaries found
        """
        try:
            page = await self.get_authenticated_page()
            if not page:
                print("Failed to get authenticated page for Reddit account search")
                return []
            
            all_accounts = []
            
            for term in search_terms[:5]:
                try:
                    print(f"Searching Reddit for: {term}")
                    
                    # Search users
                    print(f"  - Searching users...")
                    user_accounts = await self._search_users_by_term(page, term)
                    all_accounts.extend(user_accounts)
                    print(f"    Found {len(user_accounts)} user(s)")
                    await asyncio.sleep(2)
                    
                    # Search communities
                    print(f"  - Searching communities...")
                    communities = await self._search_communities_by_term(page, term)
                    all_accounts.extend(communities)
                    print(f"    Found {len(communities)} community(ies)")
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    print(f"Failed to search for term '{term}': {e}")
                    continue
            
            # Remove duplicates based on username/name
            unique_accounts = []
            seen_identifiers = set()
            
            for account in all_accounts:
                identifier = account.get('username') or account.get('name', '')
                if identifier and identifier not in seen_identifiers:
                    seen_identifiers.add(identifier)
                    unique_accounts.append(account)
            
            await page.close()
            return unique_accounts
            
        except Exception as e:
            print(f"Failed to search Reddit accounts: {e}")
            return []
    
    async def _search_users_by_term(self, page: Page, search_term: str) -> List[Dict[str, Any]]:
        """Search for user accounts using a specific term"""
        try:
            search_url = f"{self.reddit_config.base_url}/search/?q={search_term}&type=user&sort=relevance"
            success = await self.browser_manager.navigate_with_url_focus(page, search_url)
            if not success:
                return []
            
            await asyncio.sleep(3)
            accounts = await self._extract_users_from_search_results(page)
            return accounts
            
        except Exception as e:
            print(f"Failed to search users by term '{search_term}': {e}")
            return []
    
    async def _search_communities_by_term(self, page: Page, search_term: str) -> List[Dict[str, Any]]:
        """Search for communities (subreddits) using a specific term"""
        try:
            search_url = f"{self.reddit_config.base_url}/search/?q={search_term}&type=sr&sort=relevance"
            success = await self.browser_manager.navigate_with_url_focus(page, search_url)
            if not success:
                return []
            
            await asyncio.sleep(3)
            communities = await self._extract_communities_from_search_results(page)
            return communities
            
        except Exception as e:
            print(f"Failed to search communities by term '{search_term}': {e}")
            return []
    
    async def _extract_users_from_search_results(self, page: Page) -> List[Dict[str, Any]]:
        """Extract user account information from Reddit user search results"""
        try:
            accounts = []
            user_selectors = [
                '[data-testid="user-search-result"]',
                '.search-result-user',
                '.User',
                '[data-click-id="user"]',
                'a[href*="/user/"]',
                'a[href*="/u/"]'
            ]
            
            user_elements = []
            for selector in user_selectors:
                user_elements = await page.query_selector_all(selector)
                if user_elements:
                    break
            
            if not user_elements:
                user_elements = await page.query_selector_all('.search-result, [data-testid="search-result"]')
            
            for user_element in user_elements[:20]:
                try:
                    account = await self._extract_user_from_element(page, user_element)
                    if account:
                        accounts.append(account)
                except Exception as e:
                    continue
            
            return accounts
            
        except Exception as e:
            print(f"Failed to extract users from search results: {e}")
            return []
    
    async def _extract_communities_from_search_results(self, page: Page) -> List[Dict[str, Any]]:
        """Extract community information from Reddit community search results"""
        try:
            communities = []
            community_selectors = [
                '[data-testid="subreddit-search-result"]',
                '.search-result-subreddit',
                '.Subreddit',
                '[data-click-id="subreddit"]',
                'a[href*="/r/"]'
            ]
            
            community_elements = []
            for selector in community_selectors:
                community_elements = await page.query_selector_all(selector)
                if community_elements:
                    break
            
            if not community_elements:
                community_elements = await page.query_selector_all('.search-result, [data-testid="search-result"]')
            
            for community_element in community_elements[:20]:
                try:
                    community = await self._extract_community_from_element(page, community_element)
                    if community:
                        communities.append(community)
                except Exception as e:
                    continue
            
            return communities
            
        except Exception as e:
            print(f"Failed to extract communities from search results: {e}")
            return []
    
    async def _extract_user_from_element(self, page: Page, element: ElementHandle) -> Optional[Dict[str, Any]]:
        """Extract user account information from a search result element"""
        try:
            username_selectors = [
                'a[href*="/user/"]',
                'a[href*="/u/"]',
                '.username',
                '[data-testid="username"]'
            ]
            
            username = ""
            profile_url = ""
            
            for selector in username_selectors:
                username_element = await element.query_selector(selector)
                if username_element:
                    username_text = await username_element.text_content()
                    if username_text:
                        username = username_text.strip().replace('u/', '').replace('/u/', '').replace('r/', '')
                        # Skip if it's a subreddit link
                        href = await username_element.get_attribute('href')
                        if href and '/r/' in href:
                            continue
                        profile_url = href
                        if profile_url and not profile_url.startswith('http'):
                            profile_url = f"{self.reddit_config.base_url}{profile_url}"
                        break
            
            if not username:
                return None
            
            bio_description = ""
            karma_element = await element.query_selector('.karma, [data-testid="karma"]')
            if karma_element:
                karma_text = await karma_element.text_content()
                if karma_text:
                    bio_description = f"Karma: {karma_text.strip()}"
            
            return {
                'platform': 'reddit',
                'type': 'user',
                'username': username,
                'display_name': username,
                'profile_url': profile_url or f"{self.reddit_config.base_url}/user/{username}",
                'bio_description': bio_description
            }
            
        except Exception as e:
            return None
    
    async def _extract_community_from_element(self, page: Page, element: ElementHandle) -> Optional[Dict[str, Any]]:
        """Extract community information from a search result element"""
        try:
            community_selectors = [
                'a[href*="/r/"]',
                '.subreddit-name',
                '[data-testid="subreddit-name"]'
            ]
            
            community_name = ""
            community_url = ""
            
            for selector in community_selectors:
                community_element = await element.query_selector(selector)
                if community_element:
                    community_text = await community_element.text_content()
                    if community_text:
                        community_name = community_text.strip().replace('r/', '').replace('/r/', '')
                        # Skip if it's a user link
                        href = await community_element.get_attribute('href')
                        if href and ('/user/' in href or '/u/' in href):
                            continue
                        community_url = href
                        if community_url and not community_url.startswith('http'):
                            community_url = f"{self.reddit_config.base_url}{community_url}"
                        break
            
            if not community_name:
                return None
            
            description = ""
            desc_element = await element.query_selector('.description, [data-testid="subreddit-description"]')
            if desc_element:
                desc_text = await desc_element.text_content()
                if desc_text:
                    description = desc_text.strip()
            
            members_element = await element.query_selector('.members, [data-testid="subreddit-members"]')
            if members_element:
                members_text = await members_element.text_content()
                if members_text:
                    description = f"{description} | Members: {members_text.strip()}".strip()
            
            return {
                'platform': 'reddit',
                'type': 'community',
                'username': f"r/{community_name}",
                'name': community_name,
                'display_name': f"r/{community_name}",
                'profile_url': community_url or f"{self.reddit_config.base_url}/r/{community_name}",
                'bio_description': description
            }
            
        except Exception as e:
            return None
    
    async def get_account_details(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific Reddit account"""
        try:
            page = await self.get_authenticated_page()
            if not page:
                return None
            
            profile_url = f"{self.reddit_config.base_url}/user/{account_id}"
            success = await self.browser_manager.navigate_with_url_focus(page, profile_url)
            if not success:
                await page.close()
                return None
            
            await asyncio.sleep(3)
            account = await self._extract_detailed_account_info(page, account_id)
            await page.close()
            return account
            
        except Exception as e:
            print(f"Failed to get account details for {account_id}: {e}")
            return None
    
    async def _extract_detailed_account_info(self, page: Page, username: str) -> Optional[Dict[str, Any]]:
        """Extract detailed account information from Reddit profile page"""
        try:
            if "This user has deleted their account" in await page.content():
                return None
            
            display_name = username
            display_name_element = await page.query_selector('h1, .profile-name, [data-testid="profile-name"]')
            if display_name_element:
                display_name_text = await display_name_element.text_content()
                if display_name_text and display_name_text.strip():
                    display_name = display_name_text.strip()
            
            bio_description = ""
            bio_selectors = ['.profile-description', '[data-testid="profile-description"]', '.user-bio', '.profile-bio']
            for selector in bio_selectors:
                bio_element = await page.query_selector(selector)
                if bio_element:
                    bio_text = await bio_element.text_content()
                    if bio_text and bio_text.strip():
                        bio_description = bio_text.strip()
                        break
            
            return {
                'platform': 'reddit',
                'username': username,
                'display_name': display_name,
                'profile_url': f"{self.reddit_config.base_url}/user/{username}",
                'bio_description': bio_description
            }
            
        except Exception as e:
            print(f"Failed to extract detailed account info: {e}")
            return None
