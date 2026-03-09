"""
Enhanced session management for persistent login across social media platforms
"""
import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from pathlib import Path
from playwright.async_api import BrowserContext, Page

from .browser import BrowserManager
from .config import ScrapingConfig


class EnhancedSessionManager:
    """Enhanced session management with automatic persistence and validation"""
    
    def __init__(self, browser_manager: BrowserManager, config: ScrapingConfig):
        self.browser_manager = browser_manager
        self.config = config
        self.persistent_sessions_dir = Path("persistent_sessions")
        self.sessions_dir = Path("sessions")
        self._session_cache: Dict[str, Dict[str, Any]] = {}
        
        # Ensure directories exist
        self.persistent_sessions_dir.mkdir(exist_ok=True)
        self.sessions_dir.mkdir(exist_ok=True)
    
    def get_session_file_path(self, platform: str) -> Path:
        """Get the session file path for a platform"""
        platform_dir = self.persistent_sessions_dir / platform.lower()
        platform_dir.mkdir(exist_ok=True)
        return platform_dir / "session.json"
    
    def get_legacy_session_path(self, platform: str) -> Path:
        """Get legacy session file path for backward compatibility"""
        return self.sessions_dir / f"{platform.lower()}_session.json"
    
    async def check_existing_session(self, platform: str) -> bool:
        """
        Check if a valid session exists for the platform
        
        Args:
            platform: Platform name (reddit, instagram, x)
            
        Returns:
            bool: True if valid session exists, False otherwise
        """
        try:
            session_file = self.get_session_file_path(platform)
            legacy_session_file = self.get_legacy_session_path(platform)
            
            # Check new session format first
            if session_file.exists():
                return await self._validate_session_file(session_file, platform)
            
            # Check legacy session format
            if legacy_session_file.exists():
                # Migrate legacy session to new format
                if await self._migrate_legacy_session(platform):
                    return await self._validate_session_file(session_file, platform)
            
            return False
            
        except Exception as e:
            print(f"Error checking session for {platform}: {e}")
            return False
    
    async def load_persistent_session(self, platform: str) -> bool:
        """
        Load persistent session for a platform
        
        Args:
            platform: Platform name
            
        Returns:
            bool: True if session loaded successfully, False otherwise
        """
        try:
            if not await self.check_existing_session(platform):
                return False
            
            session_file = self.get_session_file_path(platform)
            
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            # Extract storage state
            storage_state = session_data.get('storage_state')
            if not storage_state:
                print(f"No storage state found in session for {platform}")
                return False
            
            # Create browser context with session
            context = await self.browser_manager.create_context(
                platform=platform,
                session_path=None  # We'll set storage state manually
            )
            
            # Apply storage state to context
            await context.add_cookies(storage_state.get('cookies', []))
            
            # Store session info in cache
            self._session_cache[platform] = {
                'loaded_at': datetime.now(),
                'session_data': session_data,
                'context': context
            }
            
            print(f"Persistent session loaded for {platform}")
            return True
            
        except Exception as e:
            print(f"Failed to load persistent session for {platform}: {e}")
            return False
    
    async def save_session_data(self, platform: str, session_data: dict) -> bool:
        """
        Save session data for a platform
        
        Args:
            platform: Platform name
            session_data: Session data to save
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            session_file = self.get_session_file_path(platform)
            
            # Get current context for the platform
            context = await self.browser_manager.get_context(platform)
            if context:
                storage_state = await context.storage_state()
                session_data['storage_state'] = storage_state
            
            # Add metadata
            session_data.update({
                'platform': platform,
                'saved_at': datetime.now().isoformat(),
                'version': '2.0'  # Enhanced session format
            })
            
            # Save to file
            with open(session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            # Update cache
            self._session_cache[platform] = {
                'loaded_at': datetime.now(),
                'session_data': session_data,
                'context': context
            }
            
            print(f"Session data saved for {platform}")
            return True
            
        except Exception as e:
            print(f"Failed to save session data for {platform}: {e}")
            return False
    
    async def prompt_manual_login(self, platform: str) -> bool:
        """
        Prompt for manual login when no valid session exists
        
        Args:
            platform: Platform name
            
        Returns:
            bool: True if manual login should proceed, False otherwise
        """
        print(f"\n{'='*50}")
        print(f"MANUAL LOGIN REQUIRED FOR {platform.upper()}")
        print(f"{'='*50}")
        print(f"No valid session found for {platform}.")
        print(f"Please log in manually through the browser.")
        print(f"Session will be saved automatically after successful login.")
        print(f"{'='*50}\n")
        
        # For now, return True to indicate manual login should proceed
        # In a GUI application, this would show a login dialog
        return True
    
    async def validate_session(self, platform: str) -> bool:
        """
        Validate that a session is still active and working
        
        Args:
            platform: Platform name
            
        Returns:
            bool: True if session is valid, False otherwise
        """
        try:
            # Check if session exists in cache
            if platform not in self._session_cache:
                return await self.check_existing_session(platform)
            
            cached_session = self._session_cache[platform]
            context = cached_session.get('context')
            
            if not context:
                return False
            
            # Create a test page to validate session
            page = await context.new_page()
            
            # Platform-specific validation
            validation_result = await self._validate_platform_session(platform, page)
            
            await page.close()
            return validation_result
            
        except Exception as e:
            print(f"Session validation failed for {platform}: {e}")
            return False
    
    async def get_session_info(self, platform: str) -> Dict[str, Any]:
        """
        Get detailed information about a platform's session
        
        Args:
            platform: Platform name
            
        Returns:
            Dict containing session information
        """
        session_file = self.get_session_file_path(platform)
        legacy_file = self.get_legacy_session_path(platform)
        
        info = {
            'platform': platform,
            'session_exists': False,
            'session_file_path': str(session_file),
            'session_age_hours': None,
            'session_valid': False,
            'cached': platform in self._session_cache,
            'legacy_session_exists': legacy_file.exists()
        }
        
        try:
            if session_file.exists():
                info['session_exists'] = True
                
                # Get file age
                stat = session_file.stat()
                age = datetime.now() - datetime.fromtimestamp(stat.st_mtime)
                info['session_age_hours'] = age.total_seconds() / 3600
                
                # Check if session is valid
                info['session_valid'] = await self.validate_session(platform)
                
                # Get session metadata
                with open(session_file, 'r') as f:
                    session_data = json.load(f)
                    info['saved_at'] = session_data.get('saved_at')
                    info['version'] = session_data.get('version', '1.0')
        
        except Exception as e:
            info['error'] = str(e)
        
        return info
    
    async def clear_session(self, platform: str) -> bool:
        """
        Clear session data for a platform
        
        Args:
            platform: Platform name
            
        Returns:
            bool: True if cleared successfully
        """
        try:
            session_file = self.get_session_file_path(platform)
            legacy_file = self.get_legacy_session_path(platform)
            
            # Remove session files
            if session_file.exists():
                session_file.unlink()
            
            if legacy_file.exists():
                legacy_file.unlink()
            
            # Clear from cache
            if platform in self._session_cache:
                del self._session_cache[platform]
            
            print(f"Session cleared for {platform}")
            return True
            
        except Exception as e:
            print(f"Failed to clear session for {platform}: {e}")
            return False
    
    async def get_all_sessions_info(self) -> Dict[str, Dict[str, Any]]:
        """Get session information for all platforms"""
        platforms = ['reddit', 'instagram', 'x']
        return {
            platform: await self.get_session_info(platform)
            for platform in platforms
        }
    
    async def _validate_session_file(self, session_file: Path, platform: str) -> bool:
        """Validate that a session file is properly formatted and not expired"""
        try:
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            # Check required fields
            if 'storage_state' not in session_data:
                return False
            
            # Check session age (expire after 30 days)
            saved_at = session_data.get('saved_at')
            if saved_at:
                saved_time = datetime.fromisoformat(saved_at)
                if datetime.now() - saved_time > timedelta(days=30):
                    print(f"Session expired for {platform} (older than 30 days)")
                    return False
            
            return True
            
        except Exception as e:
            print(f"Session file validation failed for {platform}: {e}")
            return False
    
    async def _migrate_legacy_session(self, platform: str) -> bool:
        """Migrate legacy session format to new enhanced format"""
        try:
            legacy_file = self.get_legacy_session_path(platform)
            new_file = self.get_session_file_path(platform)
            
            if not legacy_file.exists():
                return False
            
            with open(legacy_file, 'r') as f:
                legacy_data = json.load(f)
            
            # Convert to new format
            new_data = {
                'platform': platform,
                'storage_state': legacy_data,
                'saved_at': datetime.now().isoformat(),
                'version': '2.0',
                'migrated_from': 'legacy'
            }
            
            # Save in new format
            with open(new_file, 'w') as f:
                json.dump(new_data, f, indent=2)
            
            print(f"Migrated legacy session for {platform}")
            return True
            
        except Exception as e:
            print(f"Failed to migrate legacy session for {platform}: {e}")
            return False
    
    async def _validate_platform_session(self, platform: str, page: Page) -> bool:
        """Platform-specific session validation"""
        try:
            if platform.lower() == 'reddit':
                return await self._validate_reddit_session(page)
            elif platform.lower() == 'instagram':
                return await self._validate_instagram_session(page)
            elif platform.lower() == 'x':
                return await self._validate_x_session(page)
            else:
                return False
        except Exception as e:
            print(f"Platform session validation failed for {platform}: {e}")
            return False
    
    async def _validate_reddit_session(self, page: Page) -> bool:
        """Validate Reddit session by checking for logged-in indicators"""
        try:
            await page.goto('https://www.reddit.com/', timeout=10000)
            await page.wait_for_load_state('domcontentloaded')
            
            # Check for user menu or login indicators
            user_menu = await page.query_selector('[data-testid="user-menu"]')
            login_button = await page.query_selector('a[href*="login"]')
            
            # If user menu exists and no login button, session is valid
            return user_menu is not None and login_button is None
            
        except Exception:
            return False
    
    async def _validate_instagram_session(self, page: Page) -> bool:
        """Validate Instagram session by checking for logged-in indicators"""
        try:
            await page.goto('https://www.instagram.com/', timeout=10000)
            await page.wait_for_load_state('domcontentloaded')
            
            # Check for profile link or login form
            profile_link = await page.query_selector('a[href*="/accounts/edit/"]')
            login_form = await page.query_selector('form[method="post"]')
            
            # If profile settings link exists, session is valid
            return profile_link is not None
            
        except Exception:
            return False
    
    async def _validate_x_session(self, page: Page) -> bool:
        """Validate X (Twitter) session by checking for logged-in indicators"""
        try:
            await page.goto('https://x.com/', timeout=10000)
            await page.wait_for_load_state('domcontentloaded')
            
            # Check for compose tweet button or login indicators
            compose_button = await page.query_selector('[data-testid="SideNav_NewTweet_Button"]')
            login_link = await page.query_selector('a[href*="login"]')
            
            # If compose button exists, session is valid
            return compose_button is not None
            
        except Exception:
            return False