"""
Instagram Phishing Account Detection - Simplified Main Script
Just provide a CSE name and let the system do the rest
"""
import asyncio
import argparse
import json
import csv
import logging
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
from collections import defaultdict

from core.browser import BrowserManager
from core.config import ScrapingConfig, InstagramConfig
from core.models import CSEProfile
from platforms.instagram import InstagramScraper
# Removed similarity filter - saving all accounts

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('instagram_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class InstagramPhishingDetector:
    """Simplified Instagram phishing detection"""
    
    def __init__(self, headless: bool = False, output_csv: Optional[str] = None):
        self.headless = headless
        self.output_csv = output_csv
        self.browser_manager = None
        self.scraper = None
        self.csv_lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize browser and scraper"""
        scraping_config = ScrapingConfig(headless=self.headless)
        instagram_config = InstagramConfig()
        
        self.browser_manager = BrowserManager(scraping_config)
        await self.browser_manager.initialize()
        
        self.scraper = InstagramScraper(self.browser_manager, instagram_config)
        
        # Ensure logged in
        print("\n🔐 Checking Instagram login...")
        logged_in = await self.scraper.ensure_logged_in()
        
        if not logged_in:
            raise RuntimeError("Instagram login failed")
        
        print("✅ Logged in to Instagram")
    
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
        """Extract clean domain from URL"""
        import re
        domain = re.sub(r'^https?://', '', url)
        domain = re.sub(r'^www\.', '', domain)
        domain = domain.split('/')[0]
        domain = domain.split(':')[0]
        return domain
    
    def create_profile_from_name(self, cse_name: str, keywords_file: Optional[str] = None,
                                 keywords_list: Optional[List[str]] = None,
                                 canonical_url: Optional[str] = None) -> CSEProfile:
        """Create a CSE profile from just a name"""
        entity_id = cse_name.lower().replace(' ', '_')
        
        # Use canonical URL if provided, otherwise guess
        if canonical_url:
            domain_guess = self.extract_domain_from_url(canonical_url)
        else:
            domain_guess = cse_name.lower().replace(' ', '') + '.com'
        
        # Priority: keywords_list > keywords_file > cse_name
        search_keywords = [cse_name]
        
        if keywords_list:
            search_keywords = keywords_list
        elif keywords_file:
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
    
    async def search_instagram(self, profile: CSEProfile) -> List[dict]:
        """Search Instagram for accounts and detect phishing (unverified accounts)"""
        all_accounts = []
        keywords = profile.search_keywords[:10]  # Limit to 10 keywords
        
        print(f"\n🔍 Searching Instagram with {len(keywords)} keyword(s)...")
        
        for i, keyword in enumerate(keywords, 1):
            print(f"   [{i}/{len(keywords)}] Searching: \"{keyword}\"", end='', flush=True)
            
            try:
                accounts = await self.scraper.search_and_collect_accounts(keyword, None)
                all_accounts.extend(accounts)
                print(f" → Found {len(accounts)} account(s)")
            except Exception as e:
                print(f" → ❌ Error: {str(e)[:50]}")
                logger.error(f"Error searching with '{keyword}': {e}")
            
            await asyncio.sleep(3)
        
        # Remove duplicates
        unique_accounts = {acc['username']: acc for acc in all_accounts}
        all_unique = list(unique_accounts.values())
        
        # Separate verified and unverified accounts
        verified_accounts = [acc for acc in all_unique if acc.get('is_verified', False)]
        phishing_accounts = [acc for acc in all_unique if not acc.get('is_verified', False)]
        
        # Further categorize phishing accounts by risk level
        critical_risk = [acc for acc in phishing_accounts if acc.get('risk_level') == 'critical']
        high_risk = [acc for acc in phishing_accounts if acc.get('risk_level') == 'high']
        medium_risk = [acc for acc in phishing_accounts if acc.get('risk_level') == 'medium']
        
        print(f"\n📊 Account Analysis:")
        print(f"   Total unique accounts: {len(all_unique)}")
        print(f"   ✓ Verified accounts: {len(verified_accounts)}")
        print(f"   ⚠ Unverified (potential phishing): {len(phishing_accounts)}")
        if critical_risk:
            print(f"      🚨 Critical risk (fake verification claims): {len(critical_risk)}")
        if high_risk:
            print(f"      ⚠️  High risk (suspicious patterns): {len(high_risk)}")
        if medium_risk:
            print(f"      ⚠  Medium risk (unverified, no red flags): {len(medium_risk)}")
        
        if verified_accounts:
            print(f"\n✓ Verified accounts (excluded from phishing list):")
            for i, acc in enumerate(verified_accounts[:5], 1):
                print(f"      {i}. @{acc['username']} ({acc.get('display_name', 'N/A')})")
            if len(verified_accounts) > 5:
                print(f"      ... and {len(verified_accounts) - 5} more")
        
        if critical_risk:
            print(f"\n🚨 CRITICAL RISK - Fake verification claims:")
            for i, acc in enumerate(critical_risk[:5], 1):
                patterns = ', '.join(acc.get('suspicious_patterns', []))
                print(f"      {i}. @{acc['username']} - {patterns}")
            if len(critical_risk) > 5:
                print(f"      ... and {len(critical_risk) - 5} more")
        
        if high_risk:
            print(f"\n⚠️  HIGH RISK - Suspicious patterns detected:")
            for i, acc in enumerate(high_risk[:3], 1):
                patterns = ', '.join(acc.get('suspicious_patterns', []))
                print(f"      {i}. @{acc['username']} - {patterns}")
            if len(high_risk) > 3:
                print(f"      ... and {len(high_risk) - 3} more")
        
        # Return only phishing accounts (unverified)
        return phishing_accounts
    
    def display_results(self, cse_name: str, accounts: List[dict]):
        """Display phishing detection results with risk levels"""
        if not accounts:
            print(f"\n✅ No potential phishing accounts found for {cse_name}")
            return
        
        print(f"\n⚠ Found {len(accounts)} potential phishing account(s) for {cse_name}:")
        for i, acc in enumerate(accounts[:10], 1):
            risk = acc.get('risk_level', 'medium')
            risk_emoji = {'critical': '🚨', 'high': '⚠️', 'medium': '⚠', 'low': '✓'}
            patterns = acc.get('suspicious_patterns', [])
            
            if patterns:
                pattern_str = f" ({', '.join(patterns[:2])})"
            else:
                pattern_str = ""
            
            print(f"  {i}. {risk_emoji.get(risk, '⚠')} @{acc['username']} [{risk.upper()}]{pattern_str}")
        
        if len(accounts) > 10:
            print(f"  ... and {len(accounts) - 10} more account(s)")
    
    async def save_to_csv(self, cse_name: str, accounts: List[dict], csv_file: str):
        """Append accounts to CSV file with deduplication"""
        async with self.csv_lock:
            try:
                # Read existing CSV to check for duplicates
                existing_urls = set()
                file_exists = Path(csv_file).exists()
                
                if file_exists:
                    try:
                        with open(csv_file, 'r', encoding='utf-8') as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                existing_urls.add(row['url'])
                    except Exception as e:
                        logger.warning(f"Could not read existing CSV: {e}")
                
                # Filter out duplicates
                new_accounts = [acc for acc in accounts if acc['url'] not in existing_urls]
                
                if not new_accounts:
                    print(f"   No new unique accounts to add to CSV")
                    return
                
                # Append to CSV
                with open(csv_file, 'a', encoding='utf-8', newline='') as f:
                    fieldnames = ['CSE', 'platform', 'username', 'display_name', 'url', 'is_verified', 'is_phishing', 'risk_level', 'suspicious_patterns', 'bio_description', 'found_at']
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    
                    # Write header if new file
                    if not file_exists:
                        writer.writeheader()
                    
                    # Write accounts (only unverified/phishing accounts)
                    for account in new_accounts:
                        is_verified = account.get('is_verified', False)
                        suspicious_patterns = account.get('suspicious_patterns', [])
                        risk_level = account.get('risk_level', 'medium')
                        
                        writer.writerow({
                            'CSE': cse_name,
                            'platform': 'instagram',
                            'username': account.get('username', ''),
                            'display_name': account.get('display_name', ''),
                            'url': account['url'],
                            'is_verified': 'Yes' if is_verified else 'No',
                            'is_phishing': 'No' if is_verified else 'Yes',
                            'risk_level': risk_level,
                            'suspicious_patterns': '; '.join(suspicious_patterns) if suspicious_patterns else '',
                            'bio_description': account.get('bio_description', ''),
                            'found_at': account.get('found_at', datetime.now().isoformat())
                        })
                
                print(f"💾 Added {len(new_accounts)} unique account(s) to {csv_file}")
                
            except Exception as e:
                print(f"Error saving to CSV: {e}")
                import traceback
                traceback.print_exc()
    
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
    
    async def run(self, cse_name: str, output_file: str = 'instagram_results.json', 
                  keywords_file: Optional[str] = None, keywords_list: Optional[List[str]] = None,
                  canonical_url: Optional[str] = None):
        """Main execution"""
        try:
            print(f"\n{'='*60}")
            print(f"Processing: {cse_name}")
            print(f"{'='*60}")
            
            # Create profile
            profile = self.create_profile_from_name(cse_name, keywords_file, keywords_list, canonical_url)
            print(f"📝 Using {len(profile.search_keywords)} keyword(s)")
            
            # Initialize
            await self.initialize()
            
            # Search
            accounts = await self.search_instagram(profile)
            
            # Display
            self.display_results(cse_name, accounts)
            
            # Save to CSV if specified
            if self.output_csv:
                await self.save_to_csv(cse_name, accounts, self.output_csv)
            
            # Save to JSON (legacy support)
            if not self.output_csv:
                self.save_results(cse_name, accounts, output_file)
            
            print(f"\n{'='*60}")
            print("✅ Processing Complete")
            print(f"{'='*60}")
            
            return accounts
            
        finally:
            await self.close()
    
    async def run_batch(self, csv_file: str, output_file: str = 'instagram_batch_results.json'):
        """Process all CSEs from brand_map.csv"""
        cse_data = self.load_csv_data(csv_file)
        
        if not cse_data:
            print("❌ No data loaded from CSV")
            return
        
        total_cses = len(cse_data)
        print(f"\n{'='*70}")
        print(f"BATCH MODE: Instagram Scraper")
        print(f"{'='*70}")
        print(f"📊 Total CSEs: {total_cses}")
        print(f"📂 Input: {csv_file}")
        print(f"💾 Output: {output_file}")
        if self.output_csv:
            print(f"💾 CSV Output: {self.output_csv}")
        print(f"{'='*70}\n")
        
        # Initialize once for all CSEs
        await self.initialize()
        
        all_results = {}
        total_accounts_found = 0
        
        try:
            for idx, (cse_name, data) in enumerate(cse_data.items(), 1):
                print(f"\n{'='*70}")
                print(f"🎯 CSE [{idx}/{total_cses}]: {cse_name}")
                print(f"{'='*70}")
                
                keywords = data['keywords']
                canonical_url = data['canonical_url']
                print(f"📋 Keywords: {', '.join(keywords[:5])}")
                if len(keywords) > 5:
                    print(f"           ... and {len(keywords) - 5} more")
                print(f"🌐 Domain: {self.extract_domain_from_url(canonical_url)}")
                
                # Create profile with CSV keywords
                profile = self.create_profile_from_name(cse_name, keywords_list=keywords, canonical_url=canonical_url)
                
                # Search
                accounts = await self.search_instagram(profile)
                
                # Display
                self.display_results(cse_name, accounts)
                
                # Store results
                all_results[cse_name] = {
                    'timestamp': datetime.now().isoformat(),
                    'canonical_url': canonical_url,
                    'keywords_used': keywords,
                    'total_accounts': len(accounts),
                    'accounts': accounts
                }
                
                total_accounts_found += len(accounts)
                
                # Save to JSON after each CSE
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(all_results, f, indent=2, ensure_ascii=False)
                
                print(f"\n💾 Progress saved to {output_file}")
                
                # Save to CSV if specified
                if self.output_csv:
                    await self.save_to_csv(cse_name, accounts, self.output_csv)
                
                print(f"{'─'*70}")
                print(f"✅ {cse_name}: Complete ({len(accounts)} account(s))")
                print(f"{'─'*70}")
                
                # Delay between CSEs
                if idx < total_cses:
                    print(f"\n⏳ Waiting 5 seconds before next CSE...")
                    await asyncio.sleep(5)
            
            print(f"\n{'='*70}")
            print(f"✅ BATCH COMPLETE")
            print(f"{'='*70}")
            print(f"📊 CSEs processed: {total_cses}/{total_cses}")
            print(f"📊 Total accounts found: {total_accounts_found}")
            print(f"💾 Results saved to: {output_file}")
            if self.output_csv:
                print(f"💾 CSV output: {self.output_csv}")
            print(f"{'='*70}")
            
        finally:
            await self.close()


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Instagram Phishing Account Detection - Simplified',
        epilog="""
Examples:
  # Single CSE mode
  python main_instagram.py "Microsoft"
  python main_instagram.py "Bank of America" --keywords keywords.json
  python main_instagram.py "Google" --output results.json --headless
  
  # Batch mode with brand_map.csv
  python main_instagram.py --batch brand_map.csv --csv-output full_output.csv
  python main_instagram.py --batch brand_map.csv --csv-output full_output.csv --headless
        """
    )
    
    parser.add_argument('cse_name', type=str, nargs='?', help='CSE name to search for (single mode)')
    parser.add_argument('--batch', '-b', type=str, 
                       help='Process all CSEs from CSV file (brand_map.csv)')
    parser.add_argument('--keywords', '-k', type=str, 
                       help='JSON file with pre-generated keywords (single mode only)')
    parser.add_argument('--output', '-o', type=str, default='instagram_results.json',
                       help='Output JSON file (default: instagram_results.json)')
    parser.add_argument('--csv-output', '-c', type=str,
                       help='Output CSV file (e.g., full_output.csv) - appends with deduplication')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.batch and args.cse_name:
        print("❌ Error: Cannot use both batch mode and single CSE name")
        print("Use either: python main_instagram.py 'Company Name'")
        print("        or: python main_instagram.py --batch brand_map.csv")
        return
    
    if not args.batch and not args.cse_name:
        print("❌ Error: Must provide either a CSE name or --batch flag")
        print("\nExamples:")
        print("  Single: python main_instagram.py 'Microsoft'")
        print("  Batch:  python main_instagram.py --batch brand_map.csv")
        parser.print_help()
        return
    
    # Check if user accidentally provided CSV file as CSE name
    if args.cse_name and args.cse_name.endswith('.csv'):
        print(f"❌ Error: '{args.cse_name}' looks like a CSV file")
        print("For batch processing, use: python main_instagram.py --batch brand_map.csv")
        print("For single CSE, provide a company name: python main_instagram.py 'Microsoft'")
        return
    
    detector = InstagramPhishingDetector(headless=args.headless, output_csv=args.csv_output)
    
    try:
        if args.batch:
            # Batch mode
            await detector.run_batch(args.batch, args.output)
        else:
            # Single mode
            await detector.run(args.cse_name, args.output, args.keywords)
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
