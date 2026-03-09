"""
LinkedIn Company Search - Simplified Main Script
Search for companies on LinkedIn by name
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
from core.config import ScrapingConfig, LinkedinConfig
from core.models import CSEProfile
from platforms.linkedin import LinkedinScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('linkedin_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class LinkedinPhishingDetector:
    """LinkedIn company search and detection"""
    
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser_manager = None
        self.scraper = None
    
    async def initialize(self):
        """Initialize browser and scraper"""
        scraping_config = ScrapingConfig(headless=self.headless)
        linkedin_config = LinkedinConfig()
        
        self.browser_manager = BrowserManager(scraping_config)
        await self.browser_manager.initialize()
        
        self.scraper = LinkedinScraper(self.browser_manager, linkedin_config)
        
        # Ensure logged in
        print("\n🔐 Checking LinkedIn login...")
        logged_in = await self.scraper.ensure_logged_in()
        
        if not logged_in:
            raise RuntimeError("LinkedIn login failed")
        
        print("✅ Logged in to LinkedIn")
    
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
    
    def create_profile_from_name(self, cse_name: str, keywords_file: Optional[str] = None, 
                                 keywords_list: Optional[List[str]] = None) -> CSEProfile:
        """Create a CSE profile from just a name"""
        entity_id = cse_name.lower().replace(' ', '_')
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
    
    async def search_linkedin(self, profile: CSEProfile) -> List[dict]:
        """Search LinkedIn for companies"""
        all_companies = []
        keywords = profile.search_keywords[:10]  # Limit to 10 keywords
        
        print(f"\n🔍 Searching LinkedIn with {len(keywords)} keyword(s)...")
        
        for i, keyword in enumerate(keywords, 1):
            print(f"   [{i}/{len(keywords)}] Searching: \"{keyword}\"", end='', flush=True)
            
            try:
                companies = await self.scraper.search_and_collect_accounts(keyword, None)
                all_companies.extend(companies)
                print(f" → Found {len(companies)} compan{'y' if len(companies) == 1 else 'ies'}")
            except Exception as e:
                print(f" → ❌ Error: {str(e)[:50]}")
                logger.error(f"Error searching with '{keyword}': {e}")
            
            await asyncio.sleep(3)
        
        # Remove duplicates
        unique_companies = {comp.get('company_id', comp.get('username')): comp for comp in all_companies}
        result = list(unique_companies.values())
        
        if result:
            print(f"\n✅ Total: {len(result)} unique compan{'y' if len(result) == 1 else 'ies'} found")
            print(f"   First few companies:")
            for i, comp in enumerate(result[:3], 1):
                company_name = comp.get('company_name', comp.get('display_name', 'N/A'))
                company_id = comp.get('company_id', comp.get('username', 'N/A'))
                print(f"      • {company_name} ({company_id})")
            if len(result) > 3:
                print(f"      ... and {len(result) - 3} more")
        else:
            print(f"\nℹ️  No companies found")
        
        return result
    
    def display_results(self, cse_name: str, items: List[dict]):
        """Display results"""
        if not items:
            print(f"\n✅ No companies found for {cse_name}")
            return
        
        # Determine if companies or accounts
        is_company = items and 'company_id' in items[0]
        item_type = 'compan' + ('y' if len(items) == 1 else 'ies') if is_company else 'account(s)'
        
        print(f"\n📋 Found {len(items)} {item_type} for {cse_name}:")
        for i, item in enumerate(items[:10], 1):
            if is_company:
                print(f"  {i}. {item['company_name']} ({item['company_id']})")
            else:
                print(f"  {i}. @{item['username']}")
        
        if len(items) > 10:
            print(f"  ... and {len(items) - 10} more {item_type}")
    
    def save_to_csv(self, cse_name: str, companies: List[dict], csv_file: str):
        """Append companies to CSV file with deduplication"""
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
            new_companies = [c for c in companies if c['url'] not in existing_urls]
            
            if not new_companies:
                print(f"   No new unique companies to add to CSV")
                return
            
            # Append to CSV
            with open(csv_file, 'a', encoding='utf-8', newline='') as f:
                fieldnames = ['CSE', 'platform', 'username', 'display_name', 'url', 'bio_description', 'found_at']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                # Write header if new file
                if not file_exists or f.tell() == 0:
                    writer.writeheader()
                
                # Write companies
                for company in new_companies:
                    writer.writerow({
                        'CSE': cse_name,
                        'platform': 'linkedin',
                        'username': company.get('company_id', ''),
                        'display_name': company.get('company_name', ''),
                        'url': company['url'],
                        'bio_description': '',
                        'found_at': company.get('found_at', datetime.now().isoformat())
                    })
            
            print(f"💾 Added {len(new_companies)} unique compan{'y' if len(new_companies) == 1 else 'ies'} to {csv_file}")
            
        except Exception as e:
            print(f"Error saving to CSV: {e}")
            import traceback
            traceback.print_exc()
    
    def save_results(self, cse_name: str, items: List[dict], output_file: str):
        """Save results to JSON"""
        # Determine if companies or accounts
        is_company = items and 'company_id' in items[0]
        item_type = 'companies' if is_company else 'accounts'
        
        results = {
            'entity_name': cse_name,
            'timestamp': datetime.now().isoformat(),
            f'total_{item_type}': len(items),
            item_type: items
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
    
    async def run(self, cse_name: str, output_file: str = 'linkedin_results.json', 
                  keywords_file: Optional[str] = None, keywords_list: Optional[List[str]] = None,
                  csv_output: Optional[str] = None):
        """Main execution"""
        try:
            print(f"\n{'='*60}")
            print(f"Processing: {cse_name}")
            print(f"{'='*60}")
            
            # Create profile
            profile = self.create_profile_from_name(cse_name, keywords_file, keywords_list)
            print(f"📝 Using {len(profile.search_keywords)} keyword(s)")
            
            # Initialize
            await self.initialize()
            
            # Search
            companies = await self.search_linkedin(profile)
            
            # Display
            self.display_results(cse_name, companies)
            
            # Save to JSON
            self.save_results(cse_name, companies, output_file)
            
            # Save to CSV if specified
            if csv_output:
                self.save_to_csv(cse_name, companies, csv_output)
            
            print(f"\n{'='*60}")
            print("✅ Processing Complete")
            print(f"{'='*60}")
            
            return companies
            
        finally:
            await self.close()
    
    async def run_batch(self, csv_file: str, output_file: str = 'linkedin_batch_results.json',
                       csv_output: Optional[str] = None):
        """Process all CSEs from brand_map.csv"""
        cse_data = self.load_csv_data(csv_file)
        
        if not cse_data:
            print("❌ No data loaded from CSV")
            return
        
        total_cses = len(cse_data)
        print(f"\n{'='*70}")
        print(f"BATCH MODE: LinkedIn Scraper")
        print(f"{'='*70}")
        print(f"📊 Total CSEs: {total_cses}")
        print(f"📂 Input: {csv_file}")
        print(f"💾 Output: {output_file}")
        if csv_output:
            print(f"💾 CSV Output: {csv_output}")
        print(f"{'='*70}\n")
        
        # Initialize once for all CSEs
        await self.initialize()
        
        all_results = {}
        total_companies_found = 0
        
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
                print(f"🌐 URL: {canonical_url}")
                
                # Create profile with CSV keywords
                profile = self.create_profile_from_name(cse_name, keywords_list=keywords)
                
                # Search
                companies = await self.search_linkedin(profile)
                
                # Display
                self.display_results(cse_name, companies)
                
                # Store results
                all_results[cse_name] = {
                    'timestamp': datetime.now().isoformat(),
                    'canonical_url': data['canonical_url'],
                    'keywords_used': keywords,
                    'total_companies': len(companies),
                    'companies': companies
                }
                
                total_companies_found += len(companies)
                
                # Save to JSON after each CSE
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(all_results, f, indent=2, ensure_ascii=False)
                
                print(f"\n💾 Progress saved to {output_file}")
                
                # Save to CSV if specified
                if csv_output:
                    self.save_to_csv(cse_name, companies, csv_output)
                
                print(f"{'─'*70}")
                print(f"✅ {cse_name}: Complete ({len(companies)} compan{'y' if len(companies) == 1 else 'ies'})")
                print(f"{'─'*70}")
                
                # Delay between CSEs
                if idx < total_cses:
                    print(f"\n⏳ Waiting 5 seconds before next CSE...")
                    await asyncio.sleep(5)
            
            print(f"\n{'='*70}")
            print(f"✅ BATCH COMPLETE")
            print(f"{'='*70}")
            print(f"📊 CSEs processed: {total_cses}/{total_cses}")
            print(f"📊 Total companies found: {total_companies_found}")
            print(f"💾 Results saved to: {output_file}")
            if csv_output:
                print(f"💾 CSV output: {csv_output}")
            print(f"{'='*70}")
            
        finally:
            await self.close()


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='LinkedIn Company Search - Find companies by name',
        epilog="""
Examples:
  # Single company search
  python main_linkedin.py "SBI"
  python main_linkedin.py "State Bank" --keywords keywords.json
  python main_linkedin.py "HDFC Bank" --output results.json --csv-output full_output.csv
  
  # Batch mode with brand_map.csv
  python main_linkedin.py --batch brand_map.csv --csv-output full_output.csv
  python main_linkedin.py --batch brand_map.csv --csv-output full_output.csv --headless
        """
    )
    
    parser.add_argument('cse_name', type=str, nargs='?', help='Company name to search for (single mode)')
    parser.add_argument('--batch', '-b', type=str, 
                       help='Process all CSEs from CSV file (brand_map.csv)')
    parser.add_argument('--keywords', '-k', type=str, 
                       help='JSON file with pre-generated keywords (single mode only)')
    parser.add_argument('--output', '-o', type=str, default='linkedin_results.json',
                       help='Output JSON file (default: linkedin_results.json)')
    parser.add_argument('--csv-output', '-c', type=str,
                       help='Output CSV file (e.g., full_output.csv) - appends with deduplication')
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.batch and args.cse_name:
        print("❌ Error: Cannot use both batch mode and single CSE name")
        print("Use either: python main_linkedin.py 'Company Name'")
        print("        or: python main_linkedin.py --batch brand_map.csv")
        return
    
    if not args.batch and not args.cse_name:
        print("❌ Error: Must provide either a company name or --batch flag")
        print("\nExamples:")
        print("  Single: python main_linkedin.py 'Microsoft'")
        print("  Batch:  python main_linkedin.py --batch brand_map.csv")
        parser.print_help()
        return
    
    detector = LinkedinPhishingDetector(headless=args.headless)
    
    try:
        if args.batch:
            # Batch mode
            await detector.run_batch(args.batch, args.output, args.csv_output)
        else:
            # Single mode
            await detector.run(args.cse_name, args.output, args.keywords, csv_output=args.csv_output)
    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
