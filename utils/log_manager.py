"""
Log Management Utilities
Handles log rotation, archiving, and analysis
"""
import gzip
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict
import csv


class LogManager:
    """Manage log files with rotation and archiving"""
    
    def __init__(self, log_dir: str = "logs", archive_dir: str = "logs/archive"):
        self.log_dir = Path(log_dir)
        self.archive_dir = Path(archive_dir)
        self.archive_dir.mkdir(parents=True, exist_ok=True)
    
    def get_log_files(self, pattern: str = "*.log") -> List[Path]:
        """Get all log files matching pattern"""
        return sorted(self.log_dir.glob(pattern))
    
    def archive_old_logs(self, days_old: int = 7, compress: bool = True):
        """Archive logs older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        archived_count = 0
        
        for log_file in self.get_log_files():
            if log_file.is_file():
                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                
                if file_time < cutoff_date:
                    archive_path = self.archive_dir / log_file.name
                    
                    if compress:
                        # Compress and archive
                        with open(log_file, 'rb') as f_in:
                            with gzip.open(f"{archive_path}.gz", 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        log_file.unlink()
                        print(f"✅ Archived and compressed: {log_file.name}")
                    else:
                        # Just move
                        shutil.move(str(log_file), str(archive_path))
                        print(f"✅ Archived: {log_file.name}")
                    
                    archived_count += 1
        
        return archived_count
    
    def get_deduplication_stats(self, log_file: Path = None) -> Dict:
        """Parse deduplication log and extract statistics"""
        if log_file is None:
            # Get most recent deduplication log
            dedup_logs = sorted(self.log_dir.glob("deduplication_*.log"))
            if not dedup_logs:
                return {}
            log_file = dedup_logs[-1]
        
        stats = {
            'new_records': 0,
            'duplicates': 0,
            'by_platform': {},
            'by_cse': {}
        }
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if '|' not in line:
                        continue
                    
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) < 4:
                        continue
                    
                    status = parts[1]
                    cse = parts[2]
                    platform = parts[3]
                    
                    if status == 'NEW':
                        stats['new_records'] += 1
                        stats['by_platform'][platform] = stats['by_platform'].get(platform, 0) + 1
                        stats['by_cse'][cse] = stats['by_cse'].get(cse, 0) + 1
                    elif status == 'DUPLICATE':
                        stats['duplicates'] += 1
        
        except Exception as e:
            print(f"Error parsing log: {e}")
        
        return stats
    
    def generate_summary_report(self, output_file: str = "logs/summary_report.txt"):
        """Generate a summary report from recent logs"""
        report_lines = []
        report_lines.append("="*60)
        report_lines.append("BATCH SCRAPER SUMMARY REPORT")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("="*60)
        report_lines.append("")
        
        # Get most recent deduplication stats
        stats = self.get_deduplication_stats()
        
        if stats:
            report_lines.append("DEDUPLICATION STATISTICS")
            report_lines.append("-"*60)
            report_lines.append(f"New records added: {stats['new_records']}")
            report_lines.append(f"Duplicates skipped: {stats['duplicates']}")
            report_lines.append("")
            
            if stats['by_platform']:
                report_lines.append("By Platform:")
                for platform, count in sorted(stats['by_platform'].items()):
                    report_lines.append(f"  {platform}: {count} new records")
                report_lines.append("")
            
            if stats['by_cse']:
                report_lines.append("Top CSEs by New Records:")
                sorted_cses = sorted(stats['by_cse'].items(), key=lambda x: x[1], reverse=True)
                for cse, count in sorted_cses[:10]:
                    report_lines.append(f"  {cse}: {count}")
                report_lines.append("")
        
        report_lines.append("="*60)
        
        # Write report
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        print(f"✅ Summary report generated: {output_file}")
        return output_file
    
    def cleanup_old_archives(self, days_old: int = 30):
        """Delete archived logs older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        deleted_count = 0
        
        for archive_file in self.archive_dir.glob("*"):
            if archive_file.is_file():
                file_time = datetime.fromtimestamp(archive_file.stat().st_mtime)
                
                if file_time < cutoff_date:
                    archive_file.unlink()
                    print(f"🗑️  Deleted old archive: {archive_file.name}")
                    deleted_count += 1
        
        return deleted_count


def main():
    """CLI for log management"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage batch scraper logs")
    parser.add_argument('--archive', type=int, metavar='DAYS',
                       help='Archive logs older than DAYS')
    parser.add_argument('--cleanup', type=int, metavar='DAYS',
                       help='Delete archives older than DAYS')
    parser.add_argument('--report', action='store_true',
                       help='Generate summary report')
    parser.add_argument('--stats', action='store_true',
                       help='Show deduplication statistics')
    
    args = parser.parse_args()
    
    manager = LogManager()
    
    if args.archive:
        count = manager.archive_old_logs(days_old=args.archive)
        print(f"✅ Archived {count} log files")
    
    if args.cleanup:
        count = manager.cleanup_old_archives(days_old=args.cleanup)
        print(f"✅ Deleted {count} old archives")
    
    if args.report:
        manager.generate_summary_report()
    
    if args.stats:
        stats = manager.get_deduplication_stats()
        if stats:
            print("\n📊 Deduplication Statistics:")
            print(f"   New records: {stats['new_records']}")
            print(f"   Duplicates: {stats['duplicates']}")
            print(f"\n   By Platform:")
            for platform, count in sorted(stats['by_platform'].items()):
                print(f"     {platform}: {count}")
        else:
            print("No deduplication logs found")


if __name__ == "__main__":
    main()
