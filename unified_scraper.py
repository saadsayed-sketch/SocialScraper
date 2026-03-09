#!/usr/bin/env python3
"""
Unified Social Media Scraper - Phishing Account Detection
Processes multiple CSEs across all platforms with real-time deduplication
"""
import asyncio
import csv
import json
import logging
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from datetime import datetime
from collections import defaultdict
import argparse

from core.browser import BrowserManager
from core.config import ScrapingConfig, InstagramConfig, FacebookConfig, LinkedinConfig, XConfig
from core.models import CSEProfile
from platforms.instagram import InstagramScraper
from platforms.facebook import FacebookScraper
from platforms.linkedin import LinkedinScraper
from platforms.x import XScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('unified_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DeduplicationEngine:
    """Real-time deduplication using in-memory set"""
    
    def __init__(self):
        self.seen_records: Set[Tuple[str, str, str]] = set()
        self.stats = {
            'total_scraped': 0,
            'new_records': 0,
            'duplicates': 0
        }
    
    def load_existing_csv(self, csv_file: str):
        """Load existing records from CSV for deduplication"""
        if not Path(csv_file).exists():
            logger.info("No existing CSV found, starting fresh")
            return
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    key = self._make_key(
                        row.get('CSE', ''),
                        row.get('platform', ''),
                        row.get('username', '')
                    )
                    self.seen_records.add(key)
            
            logger.info(f"📚 Loaded {len(self.seen_records)} existing records for deduplication")
        except Exception as e:
            logger.error(f"Error loading existing CSV: {e}")
    
    def _make_key(self, cse: str, platform: str, username: str) -> Tuple[str, str, str]:
        """Create normalized key for deduplication"""
        return (
            cse.lower().strip(),
            platform.lower().strip(),
            username.lower().strip()
        )
    
    def is_duplicate(self, cse: str, platform: str, username: str) -> bool:
        """Check if record is duplicate"""
        key = self._make_key(cse, platform, username)
        self.stats['total_scraped'] += 1
        
        if key in self.seen_records:
            self.stats['duplicates'] += 1
            return True
        
        self.seen_records.add(key)
        self.stats['new_records'] += 1
        return False


class ProgressTracker:
    """Track progress for resume capability"""
    
    def __init__(self, progress_file: str = 'progress.json'):
        self.progress_file = progress_file
        self.completed_cses: Set[str] = set()
        self.failed_cses: Dict[str, str] = {}
        self.stats: Dict = {}
    
    def load(self):
        """Load progress from file"""
        if not Path(self.progress_file).exists():
            return
        
        try:
            with open(self.progress_file, 'r') as f:
                data = json.load(f)
                self.completed_cses = set(data.get('completed_cses', []))
                self.failed_cses = data.get('failed_cses', {})
                self.stats = data.get('stats', {})
            
            logger.info(f"📂 Loaded progress: {len(self.completed_cses)} CSEs completed")
        except Exception as e:
            logger.warning(f"Could not load progress: {e}")
    
    def save(self, cse_name: str, success: bool = True, error: str = None):
        """Save progress after processing a CSE"""
        if success:
            self.completed_cses.add(cse_name)
        else:
            self.failed_cses[cse_name] = error or "Unknown error"
        
        try:
            with open(self.progress_file, 'w') as f:
                json.dump({
                    'last_run': datetime.now().isoformat(),
                    'completed_cses': list(self.completed_cses),
                    'failed_cses': self.failed_cses,
                    'stats': self.stats
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save progress: {e}")
    
    def is_completed(self, cse_name: str) -> bool:
        """Check if CSE was already completed"""
        return cse_name in self.completed_cses


class UnifiedScraper:
    """Unified scraper for all platforms with real-time deduplication"""
    
    def __init__(self, csv_file: str, output_csv: str, headless: bool = False,
                 max_concurrent: int = 3, platforms: List[str] = None,
                 resume: bool = False, manual_platforms: List[str] = None,
                 max_retries: int = 3):
        self.csv_file = csv_file
        self.output_csv = output_csv
        self.headless = headless
        self.max_concurrent = max_concurrent
        self.platforms = platforms or ['instagram', 'facebook', 'linkedin', 'x']
        self.resume = resume
        self.manual_platforms = manual_platforms or ['x', 'linkedin']  # Platforms that may need manual intervention
        self.max_retries = max_retries
        
        # Components
        self.dedup_engine = DeduplicationEngine()
        self.progress_tracker = ProgressTracker()
        
        # Platform scrapers
        self.scrapers = {}
        self.browser_managers = {}
        
        # CSV writer lock
        self.csv_lock = asyncio.Lock()
    
    def load_csv_data(self) -> Dict[str, Dict]:
        """
        Load CSV and group by CSE name
        Returns: {CSE_name: {'keywords': [...], 'canonical_url': '...'}}
        """
        cse_data = defaultdict(lambda: {'keywords': [], 'canonical_url': ''})
        
        try:
            with open(self.csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cse_name = row['CSE'].strip()
                    keyword = row['keyword'].strip()
                    canonical_url = row['canonical_url'].strip()
                    
                    cse_data[cse_name]['keywords'].append(keyword)
                    if not cse_data[cse_name]['canonical_url']:
                        cse_data[cse_name]['canonical_url'] = canonical_url
            
            logger.info(f"📂 Loaded {len(cse_data)} unique CSEs from {self.csv_file}")
            return dict(cse_data)
        except Exception as e:
            logger.error(f"Error loading CSV: {e}")
            return {}
    
    def extract_domain_from_url(self, url: str) -> str:
        """Extract clean domain from URL"""
        import re
        domain = re.sub(r'^https?://', '', url)
        domain = re.sub(r'^www\.', '', domain)
        domain = domain.split('/')[0]
        domain = domain.split(':')[0]
        return domain
    
    def create_profile_from_cse_data(self, cse_name: str, cse_data: Dict) -> CSEProfile:
        """Create CSE profile from CSV data"""
        entity_id = cse_name.lower().replace(' ', '_')
        
        canonical_url = cse_data['canonical_url']
        domain = self.extract_domain_from_url(canonical_url) if canonical_url else f"{entity_id}.com"
        
        return CSEProfile(
            entity_id=entity_id,
            entity_name=cse_name,
            entity_type='other',
            official_accounts={},
            key_personnel=[],
            official_domains=[domain],
            sector_classification='other',
            search_keywords=cse_data['keywords'][:10]  # Limit to 10 keywords
        )
    
    async def initialize_platform(self, platform: str, retry_count: int = 0) -> bool:
        """Initialize a single platform scraper with retry logic"""
        # Determine if this platform needs manual intervention (visible browser)
        needs_manual = platform in self.manual_platforms
        use_headless = self.headless and not needs_manual
        
        try:
            if needs_manual and retry_count == 0:
                print(f"\n⚠️  {platform.capitalize()} may require manual intervention")
                print(f"   Browser will open in visible mode for login")
            
            scraping_config = ScrapingConfig(headless=use_headless)
            browser_manager = BrowserManager(scraping_config)
            await browser_manager.initialize()
            
            if platform == 'instagram':
                config = InstagramConfig()
                scraper = InstagramScraper(browser_manager, config)
            elif platform == 'facebook':
                config = FacebookConfig()
                scraper = FacebookScraper(browser_manager, config)
            elif platform == 'linkedin':
                config = LinkedinConfig()
                scraper = LinkedinScraper(browser_manager, config)
            elif platform == 'x':
                config = XConfig()
                scraper = XScraper(browser_manager, config)
            else:
                logger.warning(f"Unknown platform: {platform}")
                await browser_manager.close()
                return False
            
            # Check login with timeout
            print(f"   🔐 Checking {platform.capitalize()} login...")
            if needs_manual:
                print(f"   ⏳ Waiting up to 60 seconds for manual login if needed...")
            
            logged_in = await scraper.ensure_logged_in()
            
            if logged_in:
                self.scrapers[platform] = scraper
                self.browser_managers[platform] = browser_manager
                logger.info(f"✅ {platform.capitalize()} initialized successfully")
                return True
            else:
                logger.warning(f"❌ {platform.capitalize()} login failed")
                await browser_manager.close()
                
                # Retry logic
                if retry_count < self.max_retries:
                    wait_time = 2 ** retry_count  # Exponential backoff: 1s, 2s, 4s
                    logger.info(f"🔄 Retrying {platform.capitalize()} in {wait_time}s... (attempt {retry_count + 1}/{self.max_retries})")
                    await asyncio.sleep(wait_time)
                    return await self.initialize_platform(platform, retry_count + 1)
                else:
                    logger.error(f"❌ {platform.capitalize()} failed after {self.max_retries} attempts")
                    return False
                
        except Exception as e:
            logger.error(f"❌ {platform.capitalize()} initialization error: {e}")
            
            # Retry on exception
            if retry_count < self.max_retries:
                wait_time = 2 ** retry_count
                logger.info(f"🔄 Retrying {platform.capitalize()} after error in {wait_time}s... (attempt {retry_count + 1}/{self.max_retries})")
                await asyncio.sleep(wait_time)
                return await self.initialize_platform(platform, retry_count + 1)
            else:
                logger.error(f"❌ {platform.capitalize()} failed after {self.max_retries} attempts")
                return False
    
    async def initialize_all_platforms(self):
        """Initialize all platform scrapers"""
        print("\n" + "="*60)
        print("Initializing Platform Scrapers")
        print("="*60)
        
        tasks = []
        for platform in self.platforms:
            print(f"\n🔧 Initializing {platform.capitalize()}...")
            tasks.append(self.initialize_platform(platform))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        active_count = sum(1 for r in results if r is True)
        print("\n" + "="*60)
        print(f"✅ {active_count}/{len(self.platforms)} platforms ready")
        print("="*60 + "\n")
    
    async def close_all_platforms(self):
        """Close all scrapers"""
        for platform, scraper in self.scrapers.items():
            try:
                await scraper.close()
            except Exception as e:
                logger.error(f"Error closing {platform}: {e}")
        
        for platform, browser in self.browser_managers.items():
            try:
                await browser.close()
            except Exception as e:
                logger.error(f"Error closing {platform} browser: {e}")
    
    async def scrape_platform(self, platform: str, cse_name: str, 
                             profile: CSEProfile, retry_count: int = 0) -> List[dict]:
        """Scrape a single platform for a CSE with retry logic"""
        scraper = self.scrapers.get(platform)
        if not scraper:
            logger.warning(f"   ⚠️  {platform}: Scraper not initialized, skipping")
            return []
        
        try:
            print(f"\n   🔍 {platform.upper()}: Starting search...")
            all_accounts = []
            keywords = profile.search_keywords[:5]  # Use first 5 keywords
            
            print(f"   📝 {platform.upper()}: Using {len(keywords)} keyword(s)")
            
            for idx, keyword in enumerate(keywords, 1):
                try:
                    print(f"      [{idx}/{len(keywords)}] Searching: \"{keyword}\"", end='', flush=True)
                    accounts = await scraper.search_and_collect_accounts(keyword, None)
                    all_accounts.extend(accounts)
                    print(f" → Found {len(accounts)} account(s)")
                    await asyncio.sleep(2)  # Rate limiting
                except Exception as e:
                    print(f" → ❌ Error: {str(e)[:50]}")
                    logger.error(f"   ⚠️  {platform}: Error searching with '{keyword}': {e}")
                    # Continue with other keywords even if one fails
                    continue
            
            # Remove duplicates within platform
            unique_accounts = {}
            for acc in all_accounts:
                key = acc.get('username') or acc.get('url')
                if key and key not in unique_accounts:
                    unique_accounts[key] = acc
            
            result = list(unique_accounts.values())
            
            if result:
                print(f"   ✅ {platform.upper()}: Total {len(result)} unique account(s) found")
                # Show first few accounts
                for i, acc in enumerate(result[:3], 1):
                    username = acc.get('username', 'N/A')
                    display_name = acc.get('display_name', 'N/A')
                    print(f"      • {username} ({display_name})")
                if len(result) > 3:
                    print(f"      ... and {len(result) - 3} more")
            else:
                print(f"   ℹ️  {platform.upper()}: No accounts found")
            
            return result
            
        except Exception as e:
            logger.error(f"   ❌ {platform}: Scraping error for {cse_name}: {e}")
            print(f"   ❌ {platform.upper()}: Critical error - {str(e)[:50]}")
            
            # Retry logic for critical failures
            if retry_count < 2:  # Max 2 retries for scraping
                wait_time = 5 * (retry_count + 1)  # 5s, 10s
                print(f"   🔄 {platform.upper()}: Retrying in {wait_time}s...")
                logger.info(f"   🔄 Retrying {platform} for {cse_name} in {wait_time}s...")
                await asyncio.sleep(wait_time)
                return await self.scrape_platform(platform, cse_name, profile, retry_count + 1)
            else:
                logger.error(f"   ❌ {platform}: Failed after retries, skipping")
                print(f"   ❌ {platform.upper()}: Failed after {retry_count} retries")
                return []
    
    async def write_accounts_to_csv(self, cse_name: str, platform: str, 
                                   accounts: List[dict]):
        """Write accounts to CSV with deduplication (thread-safe)"""
        async with self.csv_lock:
            try:
                file_exists = Path(self.output_csv).exists()
                
                # Filter duplicates
                new_accounts = []
                duplicate_count = 0
                for account in accounts:
                    username = account.get('username', '')
                    if not self.dedup_engine.is_duplicate(cse_name, platform, username):
                        new_accounts.append(account)
                    else:
                        duplicate_count += 1
                
                if not new_accounts:
                    if duplicate_count > 0:
                        print(f"   ℹ️  {platform.upper()}: All {duplicate_count} account(s) already in CSV (duplicates)")
                    else:
                        print(f"   ℹ️  {platform.upper()}: No accounts to write")
                    logger.info(f"   {platform}: No new unique accounts for {cse_name}")
                    return
                
                # Write to CSV
                with open(self.output_csv, 'a', newline='', encoding='utf-8') as f:
                    fieldnames = ['CSE', 'platform', 'username', 'display_name', 
                                 'url', 'bio_description', 'found_at']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    
                    if not file_exists:
                        writer.writeheader()
                    
                    for account in new_accounts:
                        writer.writerow({
                            'CSE': cse_name,
                            'platform': platform,
                            'username': account.get('username', ''),
                            'display_name': account.get('display_name', ''),
                            'url': account.get('url', ''),
                            'bio_description': account.get('bio_description', ''),
                            'found_at': account.get('found_at', datetime.now().isoformat())
                        })
                
                print(f"   💾 {platform.upper()}: Wrote {len(new_accounts)} new account(s) to CSV", end='')
                if duplicate_count > 0:
                    print(f" (skipped {duplicate_count} duplicate(s))")
                else:
                    print()
                logger.info(f"   ✅ {platform}: Wrote {len(new_accounts)} new accounts for {cse_name}")
                
            except Exception as e:
                logger.error(f"Error writing to CSV: {e}")
                print(f"   ❌ {platform.upper()}: Error writing to CSV - {str(e)[:50]}")
    
    async def process_single_cse(self, cse_name: str, cse_data: Dict):
        """Process a single CSE across all platforms in parallel with graceful failure handling"""
        try:
            print(f"\n{'='*70}")
            print(f"🎯 CSE: {cse_name}")
            print(f"{'='*70}")
            print(f"📋 Keywords: {', '.join(cse_data['keywords'][:5])}")
            if len(cse_data['keywords']) > 5:
                print(f"           ... and {len(cse_data['keywords']) - 5} more")
            print(f"🌐 Domain: {self.extract_domain_from_url(cse_data['canonical_url'])}")
            print(f"🔧 Platforms: {', '.join([p.upper() for p in self.scrapers.keys()])}")
            
            # Create profile
            profile = self.create_profile_from_cse_data(cse_name, cse_data)
            
            # Scrape all platforms in parallel
            tasks = []
            for platform in self.scrapers.keys():
                tasks.append((platform, self.scrape_platform(platform, cse_name, profile)))
            
            if not tasks:
                logger.warning(f"⚠️  No platforms available for {cse_name}, skipping")
                print(f"\n⚠️  No platforms available, skipping {cse_name}")
                self.progress_tracker.save(cse_name, success=False, error="No platforms initialized")
                return
            
            # Wait for all platforms (with exception handling)
            results = await asyncio.gather(*[task[1] for task in tasks], return_exceptions=True)
            
            # Write results (gracefully handle failures)
            print(f"\n   📊 Writing results to CSV...")
            total_accounts = 0
            total_new_accounts = 0
            successful_platforms = 0
            failed_platforms = []
            
            for (platform, _), accounts in zip(tasks, results):
                if isinstance(accounts, Exception):
                    logger.error(f"   ❌ {platform}: Exception - {accounts}")
                    print(f"   ❌ {platform.upper()}: Exception occurred")
                    failed_platforms.append(platform)
                    continue
                
                if accounts:
                    try:
                        total_accounts += len(accounts)
                        # Count new accounts before writing
                        new_count = sum(1 for acc in accounts 
                                      if not self.dedup_engine.is_duplicate(cse_name, platform, acc.get('username', '')))
                        total_new_accounts += new_count
                        
                        await self.write_accounts_to_csv(cse_name, platform, accounts)
                        successful_platforms += 1
                    except Exception as e:
                        logger.error(f"   ❌ {platform}: Failed to write results - {e}")
                        print(f"   ❌ {platform.upper()}: Failed to write results")
                        failed_platforms.append(platform)
                else:
                    # No accounts found is not a failure
                    successful_platforms += 1
            
            # Summary
            print(f"\n{'─'*70}")
            if successful_platforms > 0:
                print(f"✅ {cse_name}: Complete")
                print(f"   📊 Total found: {total_accounts} account(s)")
                print(f"   💾 New written: {total_new_accounts} account(s)")
                print(f"   🎯 Platforms: {successful_platforms}/{len(tasks)} successful")
                if failed_platforms:
                    print(f"   ⚠️  Failed: {', '.join([p.upper() for p in failed_platforms])}")
                self.progress_tracker.save(cse_name, success=True)
            else:
                print(f"❌ {cse_name}: All platforms failed")
                self.progress_tracker.save(cse_name, success=False, error="All platforms failed")
            print(f"{'─'*70}")
            
        except Exception as e:
            logger.error(f"❌ Critical error processing {cse_name}: {e}")
            print(f"\n❌ {cse_name}: Critical error - {str(e)[:50]}")
            import traceback
            traceback.print_exc()
            self.progress_tracker.save(cse_name, success=False, error=str(e))
    
    async def run(self):
        """Main execution"""
        try:
            print("\n" + "="*60)
            print("UNIFIED SOCIAL MEDIA SCRAPER")
            print("Phishing Account Detection System")
            print("="*60)
            
            # Load CSV data
            cse_data = self.load_csv_data()
            if not cse_data:
                print("❌ No CSE data loaded")
                return
            
            # Load existing records for deduplication
            self.dedup_engine.load_existing_csv(self.output_csv)
            
            # Load progress
            if self.resume:
                self.progress_tracker.load()
            
            # Filter out completed CSEs
            remaining_cses = {k: v for k, v in cse_data.items() 
                            if not self.progress_tracker.is_completed(k)}
            
            if not remaining_cses:
                print("\n✅ All CSEs already processed!")
                return
            
            print(f"📋 {len(remaining_cses)} CSE(s) to process")
            print(f"🎯 Platforms: {', '.join([p.upper() for p in self.platforms])}")
            print(f"⚡ Concurrency: {self.max_concurrent} CSE(s) at a time")
            print(f"🔄 Max retries: {self.max_retries}")
            
            # Initialize scrapers
            await self.initialize_all_platforms()
            
            if not self.scrapers:
                print("❌ No platforms initialized successfully")
                return
            
            # Process CSEs with concurrency limit
            print(f"\n🚀 Starting processing (max {self.max_concurrent} concurrent)")
            print("="*60)
            
            cse_items = list(remaining_cses.items())
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
            async def process_with_limit(cse_name, data):
                async with semaphore:
                    await self.process_single_cse(cse_name, data)
            
            tasks = [process_with_limit(name, data) for name, data in cse_items]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Summary
            print("\n" + "="*70)
            print("✅ PROCESSING COMPLETE")
            print("="*70)
            print(f"📊 Output file: {self.output_csv}")
            print(f"📊 Total accounts scraped: {self.dedup_engine.stats['total_scraped']}")
            print(f"📊 New records written: {self.dedup_engine.stats['new_records']}")
            print(f"📊 Duplicates skipped: {self.dedup_engine.stats['duplicates']}")
            
            # Platform summary
            if self.scrapers:
                print(f"\n📊 Platform Status:")
                for platform in self.platforms:
                    if platform in self.scrapers:
                        print(f"   ✅ {platform.capitalize()}: Active")
                    else:
                        print(f"   ❌ {platform.capitalize()}: Failed to initialize")
            
            # CSE summary
            completed = len(self.progress_tracker.completed_cses)
            total = len(cse_data)
            print(f"\n📊 CSE Summary:")
            print(f"   ✅ Completed: {completed}/{total}")
            
            # Failed CSEs summary
            if self.progress_tracker.failed_cses:
                print(f"   ⚠️  Failed: {len(self.progress_tracker.failed_cses)}")
                for cse, error in list(self.progress_tracker.failed_cses.items())[:3]:
                    print(f"      • {cse}: {error[:50]}")
                if len(self.progress_tracker.failed_cses) > 3:
                    print(f"      ... and {len(self.progress_tracker.failed_cses) - 3} more")
            
            print("="*70 + "\n")
            
        except KeyboardInterrupt:
            print("\n\n❌ Interrupted by user")
        except Exception as e:
            logger.error(f"Processing error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self.close_all_platforms()


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Unified Social Media Scraper - Phishing Account Detection',
        epilog="""
Examples:
  # Basic usage (X and LinkedIn will open visible browsers for manual login)
  python unified_scraper.py brand_map.csv full_output.csv
  
  # Headless mode (Instagram/Facebook headless, X/LinkedIn visible)
  python unified_scraper.py brand_map.csv full_output.csv --headless
  
  # All platforms in headless mode (may fail on X/LinkedIn)
  python unified_scraper.py brand_map.csv full_output.csv --headless --manual-platforms ""
  
  # Only specific platforms
  python unified_scraper.py brand_map.csv full_output.csv --platforms instagram,linkedin
  
  # Resume from previous run
  python unified_scraper.py brand_map.csv full_output.csv --resume --headless
  
  # Adjust parallelism and retries
  python unified_scraper.py brand_map.csv full_output.csv --concurrent 5 --retries 5
  
  # Custom manual intervention platforms
  python unified_scraper.py brand_map.csv full_output.csv --manual-platforms x
        """
    )
    
    parser.add_argument('input_csv', type=str, help='Input CSV file (brand_map.csv)')
    parser.add_argument('output_csv', type=str, help='Output CSV file for results')
    parser.add_argument('--headless', action='store_true', 
                       help='Run browsers in headless mode (faster)')
    parser.add_argument('--concurrent', '-c', type=int, default=3,
                       help='Max concurrent CSEs to process (default: 3)')
    parser.add_argument('--platforms', '-p', type=str,
                       help='Comma-separated list of platforms (default: all)')
    parser.add_argument('--resume', '-r', action='store_true',
                       help='Resume from previous run using progress.json')
    parser.add_argument('--manual-platforms', '-m', type=str,
                       help='Comma-separated list of platforms requiring manual intervention (default: x,linkedin)')
    parser.add_argument('--retries', type=int, default=3,
                       help='Max retry attempts for failed operations (default: 3)')
    
    args = parser.parse_args()
    
    # Parse platforms
    platforms = None
    if args.platforms:
        platforms = [p.strip().lower() for p in args.platforms.split(',')]
        valid_platforms = {'instagram', 'facebook', 'linkedin', 'x'}
        platforms = [p for p in platforms if p in valid_platforms]
        if not platforms:
            print("❌ No valid platforms specified")
            print(f"Valid platforms: {', '.join(valid_platforms)}")
            return
    
    # Parse manual platforms
    manual_platforms = None
    if args.manual_platforms:
        manual_platforms = [p.strip().lower() for p in args.manual_platforms.split(',')]
    
    scraper = UnifiedScraper(
        csv_file=args.input_csv,
        output_csv=args.output_csv,
        headless=args.headless,
        max_concurrent=args.concurrent,
        platforms=platforms,
        resume=args.resume,
        manual_platforms=manual_platforms,
        max_retries=args.retries
    )
    
    await scraper.run()


if __name__ == "__main__":
    asyncio.run(main())
