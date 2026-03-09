"""
X (Twitter) Phishing Account Detection - Simplified Main Script
Just provide a CSE name and let the system do the rest
"""
import asyncio
import argparse
import json
import csv
import logging
import random
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
from collections import defaultdict

from core.browser import BrowserManager
from core.config import ScrapingConfig, XConfig
from core.models import CSEProfile
from platforms.x import XScraper
# Removed similarity filter - saving all accounts

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('x_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class XPhishingDetector:
    """Simplified X (Twitter) phishing detection"""
    
    def __init__(self, headless: bool = False, output_csv: Optional[str] = None):
        self.headless = headless
        self.output_csv = output_csv
        self.browser_manager = None
        self.scraper = None
        self.csv_lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize browser and scraper"""
        scraping_config = ScrapingConfig(headless=self.headless)
        x_config = XConfig()
        
        self.browser_manager = BrowserManager(scraping_config)
        await self.browser_manager.initialize()
        
        self.scraper = XScraper(self.browser_manager, x_config)
        
        # Ensure logged in
        print("\n🔐 Checking X login...")
        logged_in = await self.scraper.ensure_logged_in()
        
        if not logged_in:
            raise RuntimeError("X login failed")
        
        print("✅ Logged in to X")
    
    async def close(self):
        """Cleanup resources"""
        if self.scraper:
            await self.scraper.close()
        if self.browser_manager:
            await self.browser_manager.close()
    
    def load_csv_data(self, csv_file: str) -> Dict[str, Dict]:
        """
        Load CSV and group by CSE name
        Returns: {CSE_name: {'keywords': [...], 'canonical_url': '...'}}
        """
        cse_data = defaultdict(lambda: {'keywords': [], 'canonical_url': ''})
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cse_name = row['CSE'].strip()
                    keyword = row['keyword'].strip()
                    canonical_url = row['canonical_url'].strip()
                    
                    cse_data[cse_name]['keywords'].append(keyword)
                    if not cse_data[cse_name]['canonical_url']:
                        cse_data[cse_name]['canonical_url'] = canonical_url
            
            print(f"📂 Loaded {len(cse_data)} CSE(s) from {csv_file}")
            return dict(cse_data)
        except Exception as e:
            logger.error(f"Error loading CSV: {e}")
            return {}
    
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
    
    def extract_domain_from_url(self, url: str) -> str:
        """Extract clean domain from URL (e.g., https://www.airtel.in/ -> airtel.in)"""
        import re
        # Remove protocol
        domain = re.sub(r'^https?://', '', url)
        # Remove www.
        domain = re.sub(r'^www\.', '', domain)
        # Remove trailing slash and path
        domain = domain.split('/')[0]
        # Remove port if present
        domain = domain.split(':')[0]
        return domain
    
    def create_profile_from_name(self, cse_name: str, keywords_file: Optional[str] = None, 
                                 cse_data: Optional[Dict] = None) -> CSEProfile:
        """Create a CSE profile from just a name or CSV data"""
        entity_id = cse_name.lower().replace(' ', '_')
        
        # Use CSV data if provided
        if cse_data:
            search_keywords = cse_data.get('keywords', [cse_name])
            canonical_url = cse_data.get('canonical_url', '')
            
            # Extract clean domain from URL
            if canonical_url:
                domain_guess = self.extract_domain_from_url(canonical_url)
            else:
                domain_guess = cse_name.lower().replace(' ', '') + '.com'
        else:
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
            official_domains=[domain_guess] if isinstance(domain_guess, str) else [domain_guess],
            sector_classification='other',
            search_keywords=search_keywords
        )
    
    async def search_x(self, profile: CSEProfile) -> List[dict]:
        """Search X for accounts with random delays to avoid bot detection"""
        all_accounts = []
        keywords = profile.search_keywords[:10]  # Limit to 10 keywords
        
        print(f"\n🔍 Searching X with {len(keywords)} keyword(s)...")
        
        for i, keyword in enumerate(keywords, 1):
            print(f"   [{i}/{len(keywords)}] Searching: \"{keyword}\"", end='', flush=True)
            
            try:
                accounts = await self.scraper.search_and_collect_accounts(keyword, None)
                all_accounts.extend(accounts)
                print(f" → Found {len(accounts)} account(s)")
            except Exception as e:
                print(f" → ❌ Error: {str(e)[:50]}")
                logger.error(f"Error searching with '{keyword}': {e}")
            
            # Random delay between searches (5-10 seconds) to avoid bot detection
            if i < len(keywords):
                delay = random.uniform(5, 10)
                print(f"      ⏳ Waiting {delay:.1f}s before next search...")
                await asyncio.sleep(delay)
        
        # Remove duplicates
        unique_accounts = {acc['username']: acc for acc in all_accounts}
        result = list(unique_accounts.values())
        
        if result:
            print(f"\n✅ Total: {len(result)} unique account(s) found")
            print(f"   First few accounts:")
            for i, acc in enumerate(result[:3], 1):
                print(f"      • @{acc['username']} ({acc.get('display_name', 'N/A')})")
            if len(result) > 3:
                print(f"      ... and {len(result) - 3} more")
        else:
            print(f"\nℹ️  No accounts found")
        
        return result
    
    async def write_accounts_to_csv(self, cse_name: str, accounts: List[dict]):
        """
        Write accounts to CSV (thread-safe, append mode with deduplication)
        Matches batch_scraper.py format
        """
        if not self.output_csv:
            return
        
        async with self.csv_lock:
            try:
                # Read existing URLs for deduplication
                existing_urls = set()
                file_exists = Path(self.output_csv).exists()
                
                if file_exists:
                    try:
                        with open(self.output_csv, 'r', encoding='utf-8') as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                existing_urls.add(row['url'])
                    except Exception as e:
                        logger.warning(f"Could not read existing CSV for deduplication: {e}")
                
                # Filter out duplicates
                new_accounts = [acc for acc in accounts if acc.get('url') not in existing_urls]
                
                if not new_accounts:
                    logger.info(f"No new unique accounts to add for {cse_name}")
                    return
                
                with open(self.output_csv, 'a', newline='', encoding='utf-8') as f:
                    fieldnames = ['CSE', 'platform', 'username', 'display_name', 
                                 'url', 'bio_description', 'found_at']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    
                    # Write header if new file
                    if not file_exists:
                        writer.writeheader()
                    
                    # Write only new unique accounts
                    for account in new_accounts:
                        writer.writerow({
                            'CSE': cse_name,
                            'platform': 'x',
                            'username': account.get('username', ''),
                            'display_name': account.get('display_name', ''),
                            'url': account.get('url', ''),
                            'bio_description': account.get('bio_description', ''),
                            'found_at': account.get('found_at', datetime.now().isoformat())
                        })
                
                logger.info(f"✅ Added {len(new_accounts)} unique X account(s) for {cse_name} to {self.output_csv}")
                
            except Exception as e:
                logger.error(f"Error writing to CSV: {e}")
    
    def display_results(self, cse_name: str, accounts: List[dict]):
        """Display results"""
        if not accounts:
            print(f"\n✅ No accounts found for {cse_name}")
            return
        
        print(f"\n📋 Found {len(accounts)} account(s) for {cse_name}:")
        for i, acc in enumerate(accounts[:10], 1):
            print(f"  {i}. @{acc['username']}")
        
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
    
    async def run(self, cse_name: str, output_file: str = 'x_results.json',
                  keywords_file: Optional[str] = None, cse_data: Optional[Dict] = None):
        """Main execution"""
        try:
            print(f"\n{'='*60}")
            print(f"Processing: {cse_name}")
            print(f"{'='*60}")
            
            # Create profile
            profile = self.create_profile_from_name(cse_name, keywords_file, cse_data)
            print(f"📝 Using {len(profile.search_keywords)} keyword(s)")
            
            # Initialize
            await self.initialize()
            
            # Search
            accounts = await self.search_x(profile)
            
            # Display
            self.display_results(cse_name, accounts)
            
            # Save to CSV if output_csv is set
            if self.output_csv:
                await self.write_accounts_to_csv(cse_name, accounts)
            
            # Save to JSON (legacy support)
            if not self.output_csv:
                self.save_results(cse_name, accounts, output_file)
            
            print(f"\n{'='*60}")
            print("✅ Processing Complete")
            print(f"{'='*60}")
            
        finally:
            await self.close()
    
    async def run_batch(self, csv_file: str):
        """Process all CSEs from brand_map.csv with anti-bot detection measures"""
        cse_data = self.load_csv_data(csv_file)
        
        if not cse_data:
            print("❌ No CSE data loaded from CSV")
            return
        
        total_cses = len(cse_data)
        print(f"\n{'='*70}")
        print(f"BATCH MODE: X (Twitter) Scraper")
        print(f"{'='*70}")
        print(f"📊 Total CSEs: {total_cses}")
        print(f"📂 Input: {csv_file}")
        if self.output_csv:
            print(f"💾 CSV Output: {self.output_csv}")
        print(f"⚠️  Using random delays (10-20s) between CSEs to avoid bot detection")
        print(f"{'='*70}\n")
        
        # Initialize once for all CSEs
        await self.initialize()
        
        total_accounts_found = 0
        
        try:
            for i, (cse_name, data) in enumerate(cse_data.items(), 1):
                print(f"\n{'='*70}")
                print(f"🎯 CSE [{i}/{total_cses}]: {cse_name}")
                print(f"{'='*70}")
                
                keywords = data['keywords']
                canonical_url = data['canonical_url']
                print(f"📋 Keywords: {', '.join(keywords[:5])}")
                if len(keywords) > 5:
                    print(f"           ... and {len(keywords) - 5} more")
                print(f"🌐 Domain: {self.extract_domain_from_url(canonical_url)}")
                
                try:
                    # Create profile
                    profile = self.create_profile_from_name(cse_name, cse_data=data)
                    
                    # Search
                    accounts = await self.search_x(profile)
                    
                    # Display
                    self.display_results(cse_name, accounts)
                    
                    total_accounts_found += len(accounts)
                    
                    # Save to CSV
                    await self.write_accounts_to_csv(cse_name, accounts)
                    
                    print(f"{'─'*70}")
                    print(f"✅ {cse_name}: Complete ({len(accounts)} account(s))")
                    print(f"{'─'*70}")
                    
                    # Random delay between CSEs (10-20 seconds) to avoid bot detection
                    if i < total_cses:
                        delay = random.uniform(10, 20)
                        print(f"\n⏳ Waiting {delay:.1f}s before next CSE...")
                        await asyncio.sleep(delay)
                    
                except Exception as e:
                    logger.error(f"Error processing {cse_name}: {e}")
                    print(f"❌ Error processing {cse_name}: {e}")
                    continue
            
            print(f"\n{'='*70}")
            print(f"✅ BATCH COMPLETE")
            print(f"{'='*70}")
            print(f"📊 CSEs processed: {total_cses}/{total_cses}")
            print(f"📊 Total accounts found: {total_accounts_found}")
            if self.output_csv:
                print(f"💾 CSV output: {self.output_csv}")
            print(f"{'='*70}")
            
        finally:
            await self.close()


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='X (Twitter) Phishing Account Detection - Simplified',
        epilog="""
Examples:
  # Single CSE mode
  python main_x.py "Microsoft"
  python main_x.py "Bank of America" --keywords keywords.json
  python main_x.py "Google" --output results.json --headless
  
  # Batch mode with brand_map.csv
  python main_x.py --batch brand_map.csv --csv-output full_output.csv
  python main_x.py --batch brand_map.csv --csv-output full_output.csv --headless
        """
    )
    
    parser.add_argument('cse_name', type=str, nargs='?', help='CSE name to search for (single mode)')
    parser.add_argument('--batch', '-b', type=str, 
                       help='Process all CSEs from CSV file (brand_map.csv)')
    parser.add_argument('--csv-output', '-c', type=str,
                       help='Output CSV file for batch mode (e.g., full_output.csv)')
    parser.add_argument('--keywords', '-k', type=str, 
                       help='JSON file with pre-generated keywords (single mode)')
    parser.add_argument('--output', '-o', type=str, default='x_results.json',
                       help='Output JSON file for single mode (default: x_results.json)')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.batch:
        # Batch mode
        if not args.csv_output:
            print("❌ Error: --csv-output is required for batch mode")
            print("Example: python main_x.py --batch brand_map.csv --csv-output full_output.csv")
            return
        
        detector = XPhishingDetector(headless=args.headless, output_csv=args.csv_output)
        
        try:
            await detector.run_batch(args.batch)
        except KeyboardInterrupt:
            print("\n\n❌ Interrupted by user")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    elif args.cse_name:
        # Single CSE mode
        detector = XPhishingDetector(headless=args.headless, output_csv=args.csv_output)
        
        try:
            await detector.run(args.cse_name, args.output, args.keywords)
        except KeyboardInterrupt:
            print("\n\n❌ Interrupted by user")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    else:
        print("❌ Error: Either provide a CSE name or use --batch mode")
        print("\nExamples:")
        print("  Single: python main_x.py 'Microsoft'")
        print("  Batch:  python main_x.py --batch brand_map.csv --csv-output full_output.csv")
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
