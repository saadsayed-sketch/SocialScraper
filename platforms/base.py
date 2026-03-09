"""
Simplified base platform module for account detection across social media platforms
"""
import asyncio
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from playwright.async_api import Page

from core.models import CSEProfile
from core.browser import BrowserManager
from core.config import ScrapingConfig
from core.session_manager import EnhancedSessionManager


class BasePlatformModule(ABC):
    """
    Abstract base class for platform-specific account detection modules
    """
    
    def __init__(self, browser_manager: BrowserManager, config: ScrapingConfig):
        self.browser_manager = browser_manager
        self.config = config
        self.session_manager = EnhancedSessionManager(browser_manager, config)
        self.platform_name = self._get_platform_name()
        self._authenticated_page: Optional[Page] = None
    
    @abstractmethod
    def _get_platform_name(self) -> str:
        """Return the platform name (e.g., 'reddit', 'instagram', 'x')"""
        pass
    
    @abstractmethod
    async def login(self, username: str, password: str) -> bool:
        """Login to the platform with username and password"""
        pass
    
    @abstractmethod
    async def search_accounts(self, search_terms: List[str]) -> List[Dict[str, Any]]:
        """Search for accounts using the provided search terms"""
        pass
    
    @abstractmethod
    async def get_account_details(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific account"""
        pass
    
    # Common interface methods with default implementations
    
    async def login_with_persistence(self) -> bool:
        """
        Login using persistent session or prompt for manual login
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            if await self.session_manager.check_existing_session(self.platform_name):
                print(f"✅ Found existing {self.platform_name} session")
                
                if await self.session_manager.load_persistent_session(self.platform_name):
                    print(f"✅ {self.platform_name} session loaded successfully")
                    return True
                else:
                    print(f"⚠️ Failed to load {self.platform_name} session, manual login required")
            else:
                print(f"ℹ️ No existing {self.platform_name} session found")
            
            return await self.session_manager.prompt_manual_login(self.platform_name)
            
        except Exception as e:
            print(f"Login with persistence failed for {self.platform_name}: {e}")
            return False
    
    async def search_accounts_by_cse(self, cse_profile: CSEProfile) -> List[Dict[str, Any]]:
        """
        Search for accounts that might be impersonating or targeting a CSE
        
        Args:
            cse_profile: Critical Sector Entity profile to search against
            
        Returns:
            List of potentially suspicious account dictionaries
        """
        try:
            search_terms = self._generate_search_terms_from_cse(cse_profile)
            found_accounts = await self.search_accounts(search_terms)
            
            # Add CSE context to each account
            for account in found_accounts:
                account['target_cse_id'] = cse_profile.entity_id
                account['similarity_score'] = self._calculate_cse_similarity(account, cse_profile)
            
            return found_accounts
            
        except Exception as e:
            print(f"Failed to search accounts by CSE for {self.platform_name}: {e}")
            return []
    
    def _generate_search_terms_from_cse(self, cse_profile: CSEProfile) -> List[str]:
        """Generate search terms from CSE profile data"""
        search_terms = set()
        
        search_terms.add(cse_profile.entity_name.lower())
        
        name_words = cse_profile.entity_name.lower().split()
        for word in name_words:
            if len(word) > 2:
                search_terms.add(word)
        
        for person in cse_profile.key_personnel:
            search_terms.add(person.lower())
            person_words = person.lower().split()
            for word in person_words:
                if len(word) > 2:
                    search_terms.add(word)
        
        for domain in cse_profile.official_domains:
            domain_name = domain.split('.')[0]
            if len(domain_name) > 2:
                search_terms.add(domain_name.lower())
        
        search_terms.update(cse_profile.search_keywords)
        
        return list(search_terms)[:20]
    
    def _calculate_cse_similarity(self, account: Dict[str, Any], cse_profile: CSEProfile) -> float:
        """Calculate similarity score between an account and CSE profile"""
        try:
            similarity_factors = []
            
            username_similarity = self._calculate_text_similarity(
                account.get('username', '').lower(),
                cse_profile.entity_name.lower()
            )
            similarity_factors.append(username_similarity * 0.4)
            
            display_name_similarity = self._calculate_text_similarity(
                account.get('display_name', '').lower(),
                cse_profile.entity_name.lower()
            )
            similarity_factors.append(display_name_similarity * 0.3)
            
            bio_similarity = 0.0
            bio_description = account.get('bio_description', '')
            if bio_description:
                bio_text = bio_description.lower()
                matches = 0
                total_terms = len(cse_profile.search_keywords)
                
                for term in cse_profile.search_keywords:
                    if term.lower() in bio_text:
                        matches += 1
                
                if total_terms > 0:
                    bio_similarity = matches / total_terms
            
            similarity_factors.append(bio_similarity * 0.2)
            
            return sum(similarity_factors)
            
        except Exception as e:
            print(f"Failed to calculate CSE similarity: {e}")
            return 0.0
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity using character overlap"""
        if not text1 or not text2:
            return 0.0
        
        set1 = set(text1.lower())
        set2 = set(text2.lower())
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    async def get_authenticated_page(self) -> Optional[Page]:
        """Get an authenticated page for platform operations"""
        if self._authenticated_page and not self._authenticated_page.is_closed():
            return self._authenticated_page
        
        try:
            context = await self.browser_manager.get_context(self.platform_name)
            if context:
                self._authenticated_page = await context.new_page()
                return self._authenticated_page
        except Exception as e:
            print(f"Failed to get authenticated page for {self.platform_name}: {e}")
        
        return None
    
    async def close(self):
        """Clean up resources"""
        if self._authenticated_page and not self._authenticated_page.is_closed():
            await self._authenticated_page.close()
            self._authenticated_page = None
