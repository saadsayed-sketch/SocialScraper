# Streamlined Social Media Scraping Workflow

## 🎯 Goal
Transform `brand_map.csv` → `flagged_output.csv` with minimal steps and maximum efficiency

**Purpose:** Identify phishing/impersonation accounts across social media platforms for security analysis and threat detection.

---

## 📊 Current Workflow Analysis

### Current Process (4 Steps)
```
brand_map.csv
    ↓
[1] batch_scraper.py (Instagram/Facebook)
    ↓
[2] main_linkedin.py --batch (LinkedIn)
    ↓
[3] main_x.py --batch (X/Twitter)
    ↓
full_output.csv
    ↓
[4] clean_duplicates.py
    ↓
full_output.csv (raw)
    ↓
[5] process_results.py (clean + flag)
    ↓
full_output_cleaned.csv
```

### Issues with Current Approach
- ❌ Multiple separate scripts for different platforms
- ❌ Manual execution of 3 different scrapers
- ❌ Separate deduplication step needed
- ❌ No unified progress tracking
- ❌ Inconsistent error handling
- ❌ X platform has bot detection issues

---

## ✨ Streamlined Workflow (2 Steps)

### Proposed Process
```
brand_map.csv
    ↓
[1] unified_scraper.py
    ├─ All platforms in parallel
    ├─ Built-in deduplication
    ├─ Progress tracking
    └─ Error recovery
    ↓
full_output.csv (raw)
    ↓
[2] process_results.py (clean + flag)
    ↓
full_output_cleaned.csv
```

### Benefits
- ✅ Single command execution
- ✅ Real-time deduplication (no separate step)
- ✅ Unified progress tracking
- ✅ Better error handling
- ✅ Faster execution (true parallelism)
- ✅ Resume capability built-in

---

## 🚀 Implementation Plan

### Step 1: Create Unified Scraper

**File:** `unified_scraper.py`

**Features:**
1. Load brand_map.csv
2. Initialize all platform scrapers once
3. Process CSEs with true parallelism:
   - All platforms for CSE1 in parallel
   - Move to CSE2 while CSE1 is still running
4. Real-time deduplication in memory
5. Append to CSV only unique records
6. Progress tracking with resume capability

**Command:**
```bash
python unified_scraper.py brand_map.csv full_output.csv --platforms instagram,facebook,linkedin,x
```

### Step 2: Process Results (Clean & Flag)

**File:** `process_results.py` (unified processing)

**Command:**
```bash
python process_results.py full_output.csv --output flagged_output.csv
```

This script does both deduplication and false positive flagging in one step.

---

## 📋 Detailed Unified Scraper Design

### Architecture
```python
UnifiedScraper
├── CSVLoader
│   └── load_brand_map() → Dict[CSE, keywords]
│
├── PlatformManager
│   ├── initialize_all_platforms()
│   ├── instagram_scraper
│   ├── facebook_scraper
│   ├── linkedin_scraper
│   └── x_scraper
│
├── DeduplicationEngine
│   ├── load_existing_records()
│   ├── check_duplicate(cse, platform, username) → bool
│   └── add_to_seen(cse, platform, username)
│
├── ProgressTracker
│   ├── load_progress()
│   ├── save_progress(cse_name)
│   └── get_remaining_cses() → List[CSE]
│
└── CSVWriter
    ├── write_header()
    └── append_accounts(accounts) → thread-safe
```

### Execution Flow
```
1. Load Configuration
   ├─ Read brand_map.csv
   ├─ Load existing full_output.csv for deduplication
   └─ Load progress.json for resume

2. Initialize Platforms (Once)
   ├─ Instagram scraper (login once)
   ├─ Facebook scraper (login once)
   ├─ LinkedIn scraper (login once)
   └─ X scraper (login once, skip if fails)

3. Process CSEs (Parallel)
   For each CSE:
   ├─ Create CSE profile
   ├─ Launch 4 parallel tasks (one per platform)
   │  ├─ Task 1: Search Instagram
   │  ├─ Task 2: Search Facebook
   │  ├─ Task 3: Search LinkedIn
   │  └─ Task 4: Search X
   ├─ Collect results from all tasks
   ├─ Deduplicate in memory
   ├─ Write unique accounts to CSV
   └─ Save progress

4. Cleanup
   ├─ Close all scrapers
   ├─ Generate summary report
   └─ Exit
```

---

## 🔧 Key Improvements

### 1. Real-time Deduplication
```python
# Load existing records at startup
existing_records = set()
if Path('full_output.csv').exists():
    with open('full_output.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row['CSE'].lower(), row['platform'], row['username'].lower())
            existing_records.add(key)

# Check before writing
def is_duplicate(cse, platform, username):
    key = (cse.lower(), platform, username.lower())
    if key in existing_records:
        return True
    existing_records.add(key)
    return False
```

### 2. True Parallelism
```python
# Process multiple CSEs simultaneously
async def process_batch(cses, max_concurrent=3):
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_with_limit(cse):
        async with semaphore:
            return await process_single_cse(cse)
    
    tasks = [process_with_limit(cse) for cse in cses]
    return await asyncio.gather(*tasks)
```

### 3. Unified Progress Tracking
```json
{
  "last_run": "2026-02-25T10:30:00",
  "completed_cses": ["Airtel", "HDFC Bank"],
  "failed_cses": {"X Platform": "bot detection"},
  "stats": {
    "total_accounts": 250,
    "by_platform": {
      "instagram": 50,
      "facebook": 120,
      "linkedin": 60,
      "x": 20
    }
  }
}
```

---

## 📈 Performance Comparison

### Current Workflow
```
Step 1: batch_scraper.py (Instagram + Facebook)
        Time: 5-10 minutes
        Output: partial_output.csv

Step 2: main_linkedin.py --batch
        Time: 10-15 minutes
        Output: append to full_output.csv

Step 3: main_x.py --batch
        Time: 15-20 minutes (with delays)
        Output: append to full_output.csv

Step 4: clean_duplicates.py
        Time: 1-2 seconds
        Output: full_output.csv (cleaned)

Step 5: process_results.py
        Time: 2-3 seconds
        Output: full_output_cleaned.csv (deduplicated + flagged)

TOTAL: 30-45 minutes + manual intervention
```

### Streamlined Workflow
```
Step 1: unified_scraper.py
        Time: 10-15 minutes (all platforms in parallel)
        Output: full_output.csv (already deduplicated)

Step 2: process_results.py
        Time: 2-3 seconds
        Output: full_output_cleaned.csv (deduplicated + flagged)

TOTAL: 10-15 minutes, fully automated
```

**Time Savings: 50-70%**

---

## 🎯 Recommended Changes

### Files to Keep (Minimal Changes)
1. ✅ `process_results.py` - Unified processing (deduplication + false positive flagging)
2. ✅ `core/` directory - Reuse existing scrapers
3. ✅ `platforms/` directory - Reuse platform logic
4. ✅ `brand_map.csv` - Input format is good

### Files to Replace
1. ❌ `batch_scraper.py` → `unified_scraper.py`
2. ❌ `main_linkedin.py` → (integrated into unified)
3. ❌ `main_x.py` → (integrated into unified)
4. ❌ `clean_duplicates.py` → (built into unified)

### Files to Remove
1. 🗑️ `batch_scraper_incremental.py` - Redundant
2. 🗑️ `main_instagram.py` - Redundant (single CSE mode)
3. 🗑️ `main_facebook.py` - Redundant (single CSE mode)
4. 🗑️ `main_reddit.py` - Not used in your workflow

---

## 📝 Usage Examples

### Complete Workflow (2 Commands)
```bash
# Step 1: Scrape all platforms
python unified_scraper.py brand_map.csv full_output.csv

# Step 2: Process results (clean + flag)
python process_results.py full_output.csv
```

### With Options
```bash
# Headless mode (faster)
python unified_scraper.py brand_map.csv full_output.csv --headless

# Select specific platforms
python unified_scraper.py brand_map.csv full_output.csv --platforms instagram,linkedin

# Resume from previous run
python unified_scraper.py brand_map.csv full_output.csv --resume

# Adjust parallelism
python unified_scraper.py brand_map.csv full_output.csv --concurrent 5
```

---

## 🔄 Migration Path

### Phase 1: Create Unified Scraper
1. Create `unified_scraper.py`
2. Integrate existing platform scrapers
3. Add real-time deduplication
4. Test with 2-3 CSEs

### Phase 2: Validate
1. Run both old and new workflows
2. Compare outputs
3. Verify deduplication works
4. Check performance improvements

### Phase 3: Switch
1. Update documentation
2. Archive old scripts
3. Use unified workflow

---

## 📊 Expected Output Format

### full_output.csv (Unified Scraper)
```csv
CSE,platform,username,display_name,url,bio_description,found_at
Airtel,instagram,airtel,Airtel,https://instagram.com/airtel,,2026-02-25T10:30:00
Airtel,facebook,AirtelIndia,Airtel India,https://facebook.com/AirtelIndia,,2026-02-25T10:30:15
Airtel,linkedin,airtel,Airtel,https://linkedin.com/company/airtel,,2026-02-25T10:30:30
HDFC Bank,instagram,hdfcbank,HDFC Bank,https://instagram.com/hdfcbank,,2026-02-25T10:31:00
```

### flagged_output.csv (After False Positive Detection)
```csv
CSE,platform,username,display_name,url,bio_description,found_at,false_positive
Airtel,instagram,airtel,Airtel,https://instagram.com/airtel,,2026-02-25T10:30:00,FALSE
Airtel,instagram,airtel_scam,Airtel Support,https://instagram.com/airtel_scam,,2026-02-25T10:30:05,TRUE
HDFC Bank,instagram,hdfcbank,HDFC Bank,https://instagram.com/hdfcbank,,2026-02-25T10:31:00,FALSE
```

---

## 🎉 Summary

### Before (Current)
- 5 separate scripts
- 4-5 manual steps
- 30-45 minutes
- Prone to errors
- Hard to resume

### After (Streamlined)
- 2 scripts total
- 2 commands
- 10-15 minutes
- Automated deduplication
- Built-in resume

### Next Steps
1. Review this proposal
2. Approve unified scraper design
3. I'll implement `unified_scraper.py`
4. Test and validate
5. Archive old scripts

---

**Ready to implement?** 🚀
