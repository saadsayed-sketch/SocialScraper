#!/bin/bash
# Incremental Batch Scraper Runner
# Use this for daily/monthly scheduled runs

echo "🚀 Starting Incremental Batch Scraper"
echo "📅 $(date)"
echo ""

# Activate virtual environment if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the incremental scraper
python batch_scraper_incremental.py

# Generate summary report
echo ""
echo "📊 Generating summary report..."
python utils/log_manager.py --report --stats

# Archive old logs (older than 7 days)
echo ""
echo "📦 Archiving old logs..."
python utils/log_manager.py --archive 7

echo ""
echo "✅ Incremental scraping complete!"
echo "📅 $(date)"
