"""
Enhanced Authentication Example - Demonstrates session persistence and manual login
Shows how to use the new authentication system with persistent sessions
"""
import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.browser import BrowserManager
from core.config import ConfigManager
from core.session_manager import EnhancedSessionManager
from platforms.reddit import RedditScraper
from platforms.instagram import InstagramScraper
from platforms.x import XScraper


async def demo_session_persistence():
    """Demonstrate session persistence across platforms"""
    
    print("🔐 Enhanced Authentication & Session Persistence Demo")
    print("=" * 60)
    
    # AUTOMATIC LOGIN DISABLED - Use manual login or persistent sessions
    print("ℹ️  Automatic login is disabled by default for security.")
    print("   This demo shows session persistence and manual login options.")
    
    # Initialize configuration
    config_manager = ConfigManager()
    base_config, reddit_config = config_manager.get_reddit_config()
    base_config.headless = True  # Set to False to see browser
    
    # Initialize browser manager
    browser_manager = BrowserManager(base_config)
    
    try:
        print("\n1. Initializing browser and session management...")
        await browser_manager.initialize()
        print("   ✓ Browser initialized with anti-detection measures")
        
        # Initialize platform modules
        platforms = {
            'reddit': RedditScraper(browser_manager, reddit_config),
            'instagram': InstagramScraper(browser_manager, base_config),
            'x': XScraper(browser_manager, base_config)
        }
        
        print(f"   ✓ Initialized {len(platforms)} platform modules")
        
        print("\n2. Checking existing session status...")
        session_status = {}
        
        for platform_name, platform_module in platforms.items():
            session_manager = platform_module.session_manager
            
            # Get detailed session information
            session_info = session_manager.get_session_info(platform_name)
            has_valid_session = await session_manager.check_existing_session(platform_name)
            
            session_status[platform_name] = {
                'has_session_file': session_info.get('session_file_exists', False),
                'session_age_hours': session_info.get('session_age_hours'),
                'is_valid': has_valid_session,
                'session_path': session_info.get('session_path', 'N/A')
            }
            
            print(f"\n   📱 {platform_name.title()}:")
            print(f"      Session file exists: {'✓' if session_status[platform_name]['has_session_file'] else '❌'}")
            if session_status[platform_name]['session_age_hours'] is not None:
                print(f"      Session age: {session_status[platform_name]['session_age_hours']:.1f} hours")
            print(f"      Session valid: {'✓' if session_status[platform_name]['is_valid'] else '❌'}")
            print(f"      Storage path: {session_status[platform_name]['session_path']}")
        
        print("\n3. Demonstrating authentication methods...")
        
        for platform_name, platform_module in platforms.items():
            print(f"\n   🔑 {platform_name.title()} Authentication:")
            
            if session_status[platform_name]['is_valid']:
                print("      ✓ Valid session found - attempting automatic login")
                try:
                    if await platform_module.login_with_persistence():
                        print("      ✓ Successfully authenticated with persistent session")
                        
                        # Demonstrate session usage
                        page = await platform_module.get_authenticated_page()
                        if page:
                            print("      ✓ Authenticated page ready for operations")
                            current_url = page.url
                            print(f"      Current URL: {current_url}")
                            await page.close()
                        else:
                            print("      ⚠️  Could not get authenticated page")
                    else:
                        print("      ❌ Session login failed")
                except Exception as e:
                    print(f"      ❌ Session login error: {e}")
            else:
                print("      ℹ️  No valid session - manual login required")
                print(f"      Manual login command: await {platform_name}_module.login(username, password)")
                print("      Session will be automatically saved after successful manual login")
        
        print("\n4. Session management features demonstration...")
        
        # Demonstrate session management capabilities
        for platform_name, platform_module in platforms.items():
            session_manager = platform_module.session_manager
            
            print(f"\n   📊 {platform_name.title()} Session Management:")
            
            # Show session validation
            is_valid = await session_manager.check_existing_session(platform_name)
            print(f"      Session validation: {'✓ Valid' if is_valid else '❌ Invalid/Missing'}")
            
            # Show session info
            session_info = session_manager.get_session_info(platform_name)
            if session_info.get('session_file_exists'):
                print(f"      Session file size: {session_info.get('file_size_kb', 0):.1f} KB")
                print(f"      Last modified: {session_info.get('last_modified', 'Unknown')}")
            
            # Demonstrate session cleanup (commented out to preserve sessions)
            # print(f"      Session cleanup available: session_manager.clear_session('{platform_name}')")
        
        print("\n5. Cross-platform session coordination...")
        
        # Show how sessions work together
        valid_sessions = [name for name, status in session_status.items() if status['is_valid']]
        invalid_sessions = [name for name, status in session_status.items() if not status['is_valid']]
        
        print(f"   ✓ Platforms with valid sessions: {len(valid_sessions)}")
        if valid_sessions:
            print(f"      {', '.join(valid_sessions)}")
        
        print(f"   ⚠️  Platforms requiring manual login: {len(invalid_sessions)}")
        if invalid_sessions:
            print(f"      {', '.join(invalid_sessions)}")
        
        print("\n6. Security features demonstration...")
        
        print("   🛡️  Security measures implemented:")
        print("      • Automatic login disabled by default")
        print("      • Environment variable usage commented out")
        print("      • Session data stored securely in persistent_sessions/")
        print("      • Session validation before use")
        print("      • Graceful fallback to manual login")
        print("      • No credentials stored in code or logs")
        
        print("\n7. Usage recommendations...")
        
        print("   💡 Best practices for authentication:")
        print("      1. Use manual login for initial authentication:")
        print("         await platform_module.login('username', 'password')")
        print("      2. Sessions are automatically saved and reused")
        print("      3. Check session validity before operations")
        print("      4. Handle authentication failures gracefully")
        print("      5. Clear sessions when switching accounts")
        
        print("\n8. Example workflow for new users...")
        
        print("   📝 Step-by-step authentication process:")
        print("      1. Initialize platform module")
        print("      2. Check for existing valid session")
        print("      3. If no session: perform manual login")
        print("      4. Session automatically saved for future use")
        print("      5. Subsequent runs use persistent session")
        print("      6. Session validation ensures reliability")
        
        print("\n✅ Enhanced authentication demo completed!")
        
        print("\n" + "="*60)
        print("KEY AUTHENTICATION FEATURES")
        print("="*60)
        print("✓ Persistent session storage across runs")
        print("✓ Automatic session validation and loading")
        print("✓ Graceful fallback to manual login")
        print("✓ Cross-platform session management")
        print("✓ Security-first approach (no auto-login)")
        print("✓ Comprehensive session information")
        print("✓ Easy integration with detection workflows")
        
    except Exception as e:
        print(f"\n❌ Authentication demo failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        print(f"\n🧹 Cleaning up resources...")
        await browser_manager.close()
        print("   ✓ Browser resources cleaned up")


async def demo_manual_login_process():
    """Demonstrate the manual login process for new users"""
    
    print("\n" + "="*60)
    print("MANUAL LOGIN PROCESS DEMONSTRATION")
    print("="*60)
    
    print("This section shows how to perform manual login when no session exists.")
    print("(This is a simulation - actual login would require real credentials)")
    
    config_manager = ConfigManager()
    base_config, reddit_config = config_manager.get_reddit_config()
    base_config.headless = True
    
    browser_manager = BrowserManager(base_config)
    
    try:
        await browser_manager.initialize()
        reddit_module = RedditScraper(browser_manager, reddit_config)
        
        print("\n1. Checking for existing session...")
        has_session = await reddit_module.session_manager.check_existing_session('reddit')
        
        if not has_session:
            print("   ❌ No valid session found")
            print("\n2. Manual login process would be:")
            print("   ```python")
            print("   # Get credentials securely (not from environment variables)")
            print("   username = input('Reddit username: ')")
            print("   password = getpass.getpass('Reddit password: ')")
            print("   ")
            print("   # Perform login")
            print("   success = await reddit_module.login(username, password)")
            print("   if success:")
            print("       print('✓ Login successful - session saved automatically')")
            print("   else:")
            print("       print('❌ Login failed - check credentials')")
            print("   ```")
            
            print("\n3. After successful login:")
            print("   • Session data automatically saved to persistent_sessions/reddit/")
            print("   • Future runs will use the saved session")
            print("   • No need to login again until session expires")
            
        else:
            print("   ✓ Valid session exists - manual login not needed")
        
    finally:
        await browser_manager.close()


if __name__ == "__main__":
    asyncio.run(demo_session_persistence())
    asyncio.run(demo_manual_login_process())