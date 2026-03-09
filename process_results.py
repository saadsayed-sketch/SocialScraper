"""
Unified script to process scraping results:
1. Clean duplicates (username+CSE+platform, URL+platform)
2. Flag false positives (verified accounts, official domains, high similarity)
3. Generate final cleaned output

Usage:
    python process_results.py full_output.csv
    python process_results.py full_output.csv --output cleaned_results.csv
    python process_results.py full_output.csv --no-backup --quiet
"""
import csv
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Set, Tuple
from urllib.parse import urlparse


class ResultsProcessor:
    """Process scraping results with deduplication and false positive detection"""
    
    def __init__(self, brand_map_file: str = 'brand_map.csv'):
        self.brand_map_file = brand_map_file
        self.official_domains = {}  # CSE -> set of official domains
        self.official_keywords = {}  # CSE -> set of official keywords
        self._load_brand_map()
    
    def _load_brand_map(self):
        """Load official domains and keywords from brand_map.csv"""
        if not Path(self.brand_map_file).exists():
            print(f"⚠️  Warning: {self.brand_map_file} not found. False positive detection will be limited.")
            return
        
        try:
            with open(self.brand_map_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cse = row.get('CSE', '').strip()
                    canonical_url = row.get('canonical_url', '').strip()
                    keyword = row.get('keyword', '').strip()
                    
                    if not cse:
                        continue
                    
                    # Extract domain from canonical URL
                    if canonical_url:
                        domain = self._extract_domain(canonical_url)
                        if domain:
                            if cse not in self.official_domains:
                                self.official_domains[cse] = set()
                            self.official_domains[cse].add(domain.lower())
                    
                    # Store official keywords
                    if keyword:
                        if cse not in self.official_keywords:
                            self.official_keywords[cse] = set()
                        self.official_keywords[cse].add(keyword.lower())
            
            print(f"✅ Loaded brand map: {len(self.official_domains)} CSEs with official domains")
        
        except Exception as e:
            print(f"⚠️  Warning: Error loading brand map: {e}")
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path
            # Remove www. prefix
            domain = re.sub(r'^www\.', '', domain)
            return domain
        except:
            return ''
    
    def _is_official_domain(self, url: str, cse: str) -> bool:
        """Check if URL belongs to official domain"""
        if not url or cse not in self.official_domains:
            return False
        
        domain = self._extract_domain(url)
        if not domain:
            return False
        
        # Check exact match or subdomain
        for official_domain in self.official_domains[cse]:
            if domain == official_domain or domain.endswith('.' + official_domain):
                return True
        
        return False
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate simple similarity score between two strings"""
        str1 = str1.lower().strip()
        str2 = str2.lower().strip()
        
        if str1 == str2:
            return 1.0
        
        # Remove common words
        remove_words = ['official', 'verified', 'real', 'authentic', 'the', 'bank', 'of', 'india']
        for word in remove_words:
            str1 = re.sub(r'\b' + word + r'\b', '', str1)
            str2 = re.sub(r'\b' + word + r'\b', '', str2)
        
        str1 = re.sub(r'\s+', '', str1)
        str2 = re.sub(r'\s+', '', str2)
        
        if not str1 or not str2:
            return 0.0
        
        # Simple character overlap
        set1 = set(str1)
        set2 = set(str2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def _flag_false_positive(self, row: Dict) -> Tuple[bool, str]:
        """
        Determine if a row is a false positive
        
        Returns:
            (is_false_positive, reason)
        """
        username = row.get('username', '').strip().lower()
        display_name = row.get('display_name', '').strip().lower()
        url = row.get('url', '').strip()
        cse = row.get('CSE', '').strip()
        verified = row.get('verified', '').strip().lower() == 'true'
        
        # Check 1: Verified account
        if verified:
            return True, 'verified_account'
        
        # Check 2: Official domain
        if self._is_official_domain(url, cse):
            return True, 'official_domain'
        
        # Check 3: Exact match with official keywords
        if cse in self.official_keywords:
            for keyword in self.official_keywords[cse]:
                if username == keyword or display_name == keyword:
                    return True, 'exact_keyword_match'
        
        # Check 4: Very high similarity to CSE name (likely official)
        cse_similarity = self._calculate_similarity(username, cse)
        if cse_similarity > 0.95:
            return True, 'high_similarity_to_cse'
        
        # Check 5: Known celebrity/popular accounts (common false positives)
        celebrity_accounts = {
            'barackobama', 'elonmusk', 'tesla', 'natgeo', 'cnnbrk', 'cnn',
            'billgates', 'jeffbezos', 'markzuckerberg', 'sundarpichai',
            'tim_cook', 'satyanadella', 'cristiano', 'leomessi', 'neymarjr',
            'kingjames', 'kanyewest', 'taylorswift13', 'katyperry', 'rihanna'
        }
        
        if username in celebrity_accounts:
            return True, 'celebrity_account'
        
        return False, ''
    
    def process(self, input_file: str, output_file: str = None, 
                backup: bool = True, verbose: bool = True) -> Dict:
        """
        Process CSV file: clean duplicates and flag false positives
        
        Returns:
            Statistics dictionary
        """
        if not Path(input_file).exists():
            print(f"❌ File not found: {input_file}")
            return {}
        
        # Determine output file
        if output_file is None:
            output_file = input_file.replace('.csv', '_cleaned.csv')
            if output_file == input_file:
                output_file = 'cleaned_output.csv'
        
        # Create backup if requested
        if backup:
            backup_file = f"{input_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            import shutil
            shutil.copy2(input_file, backup_file)
            print(f"📦 Backup created: {backup_file}")
        
        # Read and process rows
        rows = []
        seen_user_combinations = set()  # username + CSE + platform
        seen_url_combinations = set()   # URL + platform
        
        # Statistics tracking
        stats = {
            'total_rows': 0,
            'unique_rows': 0,
            'user_duplicates': 0,
            'url_duplicates': 0,
            'false_positives': 0,
            'false_positive_reasons': defaultdict(int),
            'final_count': 0
        }
        
        # Detailed tracking
        user_duplicates = defaultdict(list)
        url_duplicates = defaultdict(list)
        false_positives = []
        
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                
                if not fieldnames:
                    print(f"❌ Invalid CSV format")
                    return {}
                
                # Add false_positive column if not present
                if 'false_positive' not in fieldnames:
                    fieldnames = list(fieldnames) + ['false_positive', 'fp_reason']
                
                print(f"📖 Reading {input_file}...")
                
                for row in reader:
                    stats['total_rows'] += 1
                    username = row.get('username', '').strip()
                    cse = row.get('CSE', '').strip()
                    platform = row.get('platform', '').strip()
                    url = row.get('url', '').strip()
                    
                    # Create unique keys
                    user_key = (username.lower(), cse.lower(), platform.lower())
                    url_key = (url.lower(), platform.lower())
                    
                    is_duplicate = False
                    
                    # Check username + CSE + platform duplicate
                    if username and user_key in seen_user_combinations:
                        user_duplicates[user_key].append(row)
                        stats['user_duplicates'] += 1
                        is_duplicate = True
                    
                    # Check URL + platform duplicate
                    if url and url_key in seen_url_combinations:
                        url_duplicates[url_key].append(row)
                        stats['url_duplicates'] += 1
                        is_duplicate = True
                    
                    # Keep first occurrence
                    if not is_duplicate:
                        # Check for false positives
                        is_fp, fp_reason = self._flag_false_positive(row)
                        
                        row['false_positive'] = 'TRUE' if is_fp else 'FALSE'
                        row['fp_reason'] = fp_reason if is_fp else ''
                        
                        if is_fp:
                            stats['false_positives'] += 1
                            stats['false_positive_reasons'][fp_reason] += 1
                            false_positives.append(row)
                        
                        rows.append(row)
                        stats['unique_rows'] += 1
                        
                        if username:
                            seen_user_combinations.add(user_key)
                        if url:
                            seen_url_combinations.add(url_key)
            
            stats['final_count'] = len(rows)
            
            # Display statistics
            print(f"\n{'='*70}")
            print(f"📊 PROCESSING RESULTS")
            print(f"{'='*70}")
            print(f"Total rows read: {stats['total_rows']}")
            print(f"Unique entries: {stats['unique_rows']}")
            print(f"Duplicates removed: {stats['user_duplicates'] + stats['url_duplicates']}")
            print(f"  - By username+CSE+platform: {stats['user_duplicates']}")
            print(f"  - By URL+platform: {stats['url_duplicates']}")
            print(f"\n🚩 False Positives Flagged: {stats['false_positives']}")
            
            if stats['false_positive_reasons']:
                print(f"\n  Breakdown by reason:")
                for reason, count in sorted(stats['false_positive_reasons'].items(), 
                                           key=lambda x: x[1], reverse=True):
                    print(f"    - {reason}: {count}")
            
            print(f"\n✅ Final output: {stats['final_count']} entries")
            print(f"{'='*70}\n")
            
            # Verbose output
            if verbose:
                if user_duplicates:
                    print(f"🔍 USERNAME DUPLICATES ({stats['user_duplicates']} removed):")
                    for (username, cse, platform), dup_rows in list(user_duplicates.items())[:5]:
                        print(f"  🔸 {username} | {cse} | {platform} ({len(dup_rows)} duplicates)")
                    if len(user_duplicates) > 5:
                        print(f"  ... and {len(user_duplicates) - 5} more\n")
                
                if url_duplicates:
                    print(f"\n🔍 URL DUPLICATES ({stats['url_duplicates']} removed):")
                    for (url, platform), dup_rows in list(url_duplicates.items())[:5]:
                        url_preview = url[:60] + '...' if len(url) > 60 else url
                        print(f"  🔸 {url_preview} | {platform} ({len(dup_rows)} duplicates)")
                    if len(url_duplicates) > 5:
                        print(f"  ... and {len(url_duplicates) - 5} more\n")
                
                if false_positives:
                    print(f"\n🚩 FALSE POSITIVES SAMPLE ({min(10, len(false_positives))} of {len(false_positives)}):")
                    for fp in false_positives[:10]:
                        username = fp.get('username', 'N/A')
                        cse = fp.get('CSE', 'N/A')
                        reason = fp.get('fp_reason', 'unknown')
                        print(f"  🔸 @{username} | {cse} | Reason: {reason}")
                    print()
            
            # Write cleaned data
            with open(output_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            
            print(f"💾 Cleaned results saved to: {output_file}")
            print(f"✅ Processing complete!\n")
            
            return stats
        
        except Exception as e:
            print(f"❌ Error processing CSV: {e}")
            import traceback
            traceback.print_exc()
            return {}


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Process scraping results: clean duplicates and flag false positives',
        epilog="""
Examples:
  # Process full_output.csv (creates full_output_cleaned.csv)
  python process_results.py full_output.csv
  
  # Specify output file
  python process_results.py full_output.csv --output final_results.csv
  
  # Process without backup
  python process_results.py full_output.csv --no-backup
  
  # Quiet mode (less verbose)
  python process_results.py full_output.csv --quiet
  
  # Use custom brand map
  python process_results.py full_output.csv --brand-map my_brands.csv
        """
    )
    
    parser.add_argument('input', type=str,
                       help='Input CSV file to process')
    parser.add_argument('--output', '-o', type=str,
                       help='Output CSV file (default: input_cleaned.csv)')
    parser.add_argument('--brand-map', '-b', type=str, default='brand_map.csv',
                       help='Brand map CSV file for false positive detection (default: brand_map.csv)')
    parser.add_argument('--no-backup', action='store_true',
                       help='Skip creating backup before processing')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Suppress detailed logs')
    
    args = parser.parse_args()
    
    processor = ResultsProcessor(brand_map_file=args.brand_map)
    processor.process(
        input_file=args.input,
        output_file=args.output,
        backup=not args.no_backup,
        verbose=not args.quiet
    )


if __name__ == "__main__":
    main()
