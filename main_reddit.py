"""
Reddit Phishing Account Detection - Simplified Main Script
Just provide a CSE name and let the system do the rest
"""
import asyncio
import argparse
import json
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from core.browser import BrowserManager
from core.config import ScrapingConfig, RedditConfig
from core.models import CSEProfile
from platforms.reddit import RedditScraper
from utils.similarity import filter_accounts_by_similarity

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('reddit_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class RedditPhishingDetector:
    """Simplified Reddit phishing detection"""
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser_manager = None
        self.scraper = None
    
    async def initialize(self):
        """Initialize browser and scraper"""
        scraping_config = ScrapingConfig(headless=self.headless)
        reddit_config = RedditConfig()
        
        self.browser_manager = BrowserManager(scraping_config)
        await self.browser_manager.initialize()
        
        self.scraper = RedditScraper(self.browser_manager, reddit_config)
        
        # Ensure logged in
        print("\n🔐 Checking Reddit login...")
        logged_in = await self.scraper.login_with_persistence()
        
        if not logged_in:
            raise RuntimeError("Reddit login failed")
        
        print("✅ Logged in to Reddit")
    
    async def close(self):
        """Cleanup resources"""
        if self.scraper:
            await self.scraper.close()
        if self.browser_manager:
            await self.browser_manager.close()
    
    def load_keywords_from_json(self, json_file: str, cse_name: str) -> Optional[List[str]]:
        """Load keywords from JSON file for a specific CSE"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Try to find keywords for this CSE
            if cse_name in data:
                keywords = data[cse_name].get('keywords', [])
                if keywords:
                    print(f"📂 Loaded {len(keywords)} keywords from {json_file}")
                    return keywords
        except Exception as e:
            logger.warning(f"Could not load keywords from {json_file}: {e}")
        
        return None
    
    def create_profile_from_name(self, cse_name: str, keywords_file: Optional[str] = None) -> CSEProfile:
        """Create a CSE profile from just a name"""
        entity_id = cse_name.lower().replace(' ', '_')
        domain_guess = cse_name.lower().replace(' ', '') + '.com'
        
        # Load keywords from file if provided
        search_keywords = [cse_name]
        if keywords_file:
            loaded_keywords = self.load_keywords_from_json(keywords_file, cse_name)
            if loaded_keywords:
                search_keywords = loaded_keywords
        
        return CSEProfile(
            entity_id=entity_id,
            entity_name=cse_name,
            entity_type='other',
            official_accounts={},
            key_personnel=[],
            official_domains=[domain_guess],
            sector_classification='other',
            search_keywords=search_keywords
        )
    
    async def search_reddit(self, profile: CSEProfile) -> List[dict]:
        """Search Reddit for accounts"""
        all_accounts = []
        keywords = profile.search_keywords[:10]  # Limit to 10 keywords
        
        print(f"\n🔍 Searching Reddit with {len(keywords)} keyword(s)...")
        
        for i, keyword in enumerate(keywords, 1):
            print(f"   [{i}/{len(keywords)}] {keyword}")
            
            try:
                accounts = await self.scraper.search_accounts([keyword])
                all_accounts.extend(accounts)
                print(f"      Found {len(accounts)} account(s)")
            except Exception as e:
                print(f"      ❌ Error: {e}")
            
            await asyncio.sleep(2)
        
        # Remove duplicates
        unique_accounts = {acc['username']: acc for acc in all_accounts}
        return list(unique_accounts.values())
    
    def filter_accounts(self, accounts: List[dict], cse_name: str) -> List[dict]:
        """Filter accounts by similarity (optional - currently disabled)"""
        print(f"\n📊 Total accounts found: {len(accounts)}")
        
        # Optional: Apply similarity filter
        # filtered = filter_accounts_by_similarity(accounts, cse_name, min_similarity=0.3)
        # For now, return all accounts like Instagram does
        
        return accounts
    
    def display_results(self, cse_name: str, accounts: List[dict]):
        """Display results"""
        if not accounts:
            print(f"\n✅ No accounts found for {cse_name}")
            return
        
        print(f"\n📋 Found {len(accounts)} account(s) for {cse_name}:")
        for i, acc in enumerate(accounts[:10], 1):
            print(f"  {i}. u/{acc['username']}")
        
        if len(accounts) > 10:
            print(f"  ... and {len(accounts) - 10} more account(s)")
    
    def save_results(self, cse_name: str, accounts: List[dict], output_file: str):
        """Save results to JSON"""
        results = {
            'entity_name': cse_name,
            'timestamp': datetime.now().isoformat(),
            'total_accounts': len(accounts),
            'accounts': accounts
        }
        
        # Load existing data
        output_path = Path(output_file)
        existing_data = {}
        if output_path.exists():
            try:
                with open(output_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except:
                pass
        
        # Add new results
        existing_data[cse_name] = results
        
        # Save
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to: {output_file}")
    
    async def run(self, cse_name: str, output_file: str = 'reddit_results.json',
                  keywords_file: Optional[str] = None):
        """Main execution"""
        try:
            print(f"\n{'='*60}")
            print(f"Processing: {cse_name}")
            print(f"{'='*60}")
            
            # Create profile
            profile = self.create_profile_from_name(cse_name, keywords_file)
            print(f"📝 Using {len(profile.search_keywords)} keyword(s)")
            
            # Initialize
            await self.initialize()
            
            # Search
            accounts = await self.search_reddit(profile)
            
            # Display
            self.display_results(cse_name, accounts)
            
            # Save all accounts (no filtering)
            self.save_results(cse_name, accounts, output_file)
            
            print(f"\n{'='*60}")
            print("✅ Processing Complete")
            print(f"{'='*60}")
            
        finally:
            await self.close()


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Reddit Phishing Account Detection - Simplified',
        epilog="""
Examples:
  python main_reddit.py "Microsoft"
  python main_reddit.py "Bank of America" --keywords keywords.json
  python main_reddit.py "Google" --output results.json --headless
        """
    )
    
    parser.add_argument('cse_name', type=str, help='CSE name to search for')
    parser.add_argument('--keywords', '-k', type=str, 
                       help='JSON file with pre-generated keywords')
    parser.add_argument('--output', '-o', type=str, default='reddit_results.json',
                       help='Output JSON file (default: reddit_results.json)')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    
    args = parser.parse_args()
    
    detector = RedditPhishingDetector(headless=args.headless)
    
    try:
        await detector.run(args.cse_name, args.output, args.keywords)
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
