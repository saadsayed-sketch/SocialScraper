# Streamlined Workflow - Visual Flowchart

## 🎯 Complete Process Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         INPUT: brand_map.csv                         │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ keyword          | canonical_url              | CSE            │ │
│  │ Airtel           | https://www.airtel.in/     | Airtel         │ │
│  │ Bharti Airtel    | https://www.airtel.in/     | Airtel         │ │
│  │ HDFC Bank        | https://www.hdfcbank.com/  | HDFC Bank      │ │
│  │ ...              | ...                        | ...            │ │
│  └────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STEP 1: unified_scraper.py                        │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  [A] INITIALIZATION (Once)                                   │   │
│  │  ├─ Load brand_map.csv → Group by CSE                       │   │
│  │  ├─ Load existing full_output.csv → Dedup set               │   │
│  │  ├─ Load progress.json → Resume capability                  │   │
│  │  └─ Initialize all platform scrapers (login once)           │   │
│  │      ├─ Instagram ✅                                         │   │
│  │      ├─ Facebook ✅                                          │   │
│  │      ├─ LinkedIn ✅                                          │   │
│  │      └─ X/Twitter ⚠️ (skip if bot detection)                │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  [B] PARALLEL PROCESSING (Per CSE)                          │   │
│  │                                                               │   │
│  │  For CSE = "Airtel":                                         │   │
│  │  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │  Keywords: ["Airtel", "Bharti Airtel", ...]         │   │   │
│  │  │  Domain: airtel.in                                   │   │   │
│  │  └─────────────────────────────────────────────────────┘   │   │
│  │                                                               │   │
│  │  Launch 4 Parallel Tasks:                                    │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │   │
│  │  │Instagram │  │ Facebook │  │ LinkedIn │  │    X     │   │   │
│  │  │  Search  │  │  Search  │  │  Search  │  │  Search  │   │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │   │
│  │       │             │             │             │           │   │
│  │       ▼             ▼             ▼             ▼           │   │
│  │  ┌────────────────────────────────────────────────────┐   │   │
│  │  │  Results:                                           │   │   │
│  │  │  - Instagram: 5 accounts                            │   │   │
│  │  │  - Facebook: 12 accounts                            │   │   │
│  │  │  - LinkedIn: 3 accounts                             │   │   │
│  │  │  - X: 2 accounts                                    │   │   │
│  │  └────────────────────────────────────────────────────┘   │   │
│  │                                                               │   │
│  │  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │  [C] REAL-TIME DEDUPLICATION                        │   │   │
│  │  │                                                       │   │   │
│  │  │  For each account:                                   │   │   │
│  │  │    key = (CSE, platform, username)                  │   │   │
│  │  │    if key in existing_records:                      │   │   │
│  │  │      ❌ SKIP (duplicate)                            │   │   │
│  │  │    else:                                             │   │   │
│  │  │      ✅ ADD to write queue                          │   │   │
│  │  │      existing_records.add(key)                      │   │   │
│  │  └─────────────────────────────────────────────────────┘   │   │
│  │                                                               │   │
│  │  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │  [D] WRITE TO CSV (Thread-safe)                     │   │   │
│  │  │                                                       │   │   │
│  │  │  Append unique accounts to full_output.csv          │   │   │
│  │  │  Save progress to progress.json                     │   │   │
│  │  └─────────────────────────────────────────────────────┘   │   │
│  │                                                               │   │
│  │  Repeat for next CSE...                                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  [E] CLEANUP & SUMMARY                                       │   │
│  │  ├─ Close all scrapers                                       │   │
│  │  ├─ Generate statistics                                      │   │
│  │  └─ Log summary                                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    OUTPUT: full_output.csv                           │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ CSE    | platform  | username  | display_name | url | bio | ... │ │
│  │ Airtel | instagram | airtel    | Airtel       | ... | ... | ... │ │
│  │ Airtel | facebook  | AirtelIn  | Airtel India | ... | ... | ... │ │
│  │ Airtel | linkedin  | airtel    | Airtel       | ... | ... | ... │ │
│  │ HDFC   | instagram | hdfcbank  | HDFC Bank    | ... | ... | ... │ │
│  │ ...    | ...       | ...       | ...          | ... | ... | ... │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                    ✅ Already deduplicated                           │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│              STEP 2: process_results.py                              │
│              (Deduplication + False Positive Flagging)               │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  [A] LOAD DATA                                               │   │
│  │  ├─ Read full_output.csv                                     │   │
│  │  └─ Read brand_map.csv (for keywords)                        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  [B] SIMILARITY ANALYSIS                                     │   │
│  │                                                               │   │
│  │  For each account:                                            │   │
│  │    ┌─────────────────────────────────────────────────┐      │   │
│  │    │  Calculate similarity scores:                    │      │   │
│  │    │  - CSE name vs username                          │      │   │
│  │    │  - CSE name vs display_name                      │      │   │
│  │    │  - CSE name vs bio                               │      │   │
│  │    │  - Keywords vs all fields                        │      │   │
│  │    └─────────────────────────────────────────────────┘      │   │
│  │                                                               │   │
│  │    ┌─────────────────────────────────────────────────┐      │   │
│  │    │  Decision Logic:                                 │      │   │
│  │    │  if max_similarity < 0.75 AND no_keyword_match: │      │   │
│  │    │    ❌ FALSE POSITIVE                             │      │   │
│  │    │  else:                                            │      │   │
│  │    │    ✅ VALID ACCOUNT                              │      │   │
│  │    └─────────────────────────────────────────────────┘      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  [C] ADD FLAG COLUMN                                         │   │
│  │  └─ Add "false_positive" column (TRUE/FALSE)                │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  OUTPUT: flagged_output.csv                          │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │ CSE | platform | username | ... | false_positive              │ │
│  │ Airtel | instagram | airtel | ... | FALSE ✅                  │ │
│  │ Airtel | instagram | airtel_scam | ... | TRUE ❌              │ │
│  │ HDFC | instagram | hdfcbank | ... | FALSE ✅                  │ │
│  │ HDFC | instagram | hdfc_support | ... | TRUE ❌               │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                    ✅ Ready for analysis                             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Parallel Processing Detail

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CONCURRENT CSE PROCESSING                         │
│                                                                       │
│  Time: 0s                                                            │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  CSE 1: Airtel                                                │  │
│  │  ├─ Instagram ████████████░░░░░░░░░░ (searching...)          │  │
│  │  ├─ Facebook  ████████████░░░░░░░░░░ (searching...)          │  │
│  │  ├─ LinkedIn  ████████████░░░░░░░░░░ (searching...)          │  │
│  │  └─ X         ████████████░░░░░░░░░░ (searching...)          │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  Time: 30s                                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  CSE 1: Airtel                                                │  │
│  │  ├─ Instagram ████████████████████████ (done ✅)             │  │
│  │  ├─ Facebook  ████████████████████░░░░ (writing...)          │  │
│  │  ├─ LinkedIn  ████████████████████████ (done ✅)             │  │
│  │  └─ X         ████████████████████████ (done ✅)             │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  CSE 2: HDFC Bank                                             │  │
│  │  ├─ Instagram ████████░░░░░░░░░░░░░░░░ (searching...)        │  │
│  │  ├─ Facebook  ████████░░░░░░░░░░░░░░░░ (searching...)        │  │
│  │  ├─ LinkedIn  ████████░░░░░░░░░░░░░░░░ (searching...)        │  │
│  │  └─ X         ████████░░░░░░░░░░░░░░░░ (searching...)        │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  Time: 60s                                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  CSE 1: Airtel ✅ COMPLETE                                    │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  CSE 2: HDFC Bank                                             │  │
│  │  ├─ Instagram ████████████████████████ (done ✅)             │  │
│  │  ├─ Facebook  ████████████████████████ (done ✅)             │  │
│  │  ├─ LinkedIn  ████████████████████░░░░ (writing...)          │  │
│  │  └─ X         ████████████████████████ (done ✅)             │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  CSE 3: ICICI Bank                                            │  │
│  │  ├─ Instagram ████████░░░░░░░░░░░░░░░░ (searching...)        │  │
│  │  ├─ Facebook  ████████░░░░░░░░░░░░░░░░ (searching...)        │  │
│  │  ├─ LinkedIn  ████████░░░░░░░░░░░░░░░░ (searching...)        │  │
│  │  └─ X         ████████░░░░░░░░░░░░░░░░ (searching...)        │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ⚡ 3 CSEs processing simultaneously                                 │
│  ⚡ 12 platform searches running in parallel                         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Deduplication Logic Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DEDUPLICATION ENGINE                              │
│                                                                       │
│  STARTUP:                                                            │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Load existing full_output.csv                               │  │
│  │  ├─ Row 1: (airtel, instagram, airtel)                       │  │
│  │  ├─ Row 2: (airtel, facebook, airtelindia)                   │  │
│  │  ├─ Row 3: (hdfc bank, instagram, hdfcbank)                  │  │
│  │  └─ ... (1000 more rows)                                     │  │
│  │                                                                │  │
│  │  Create in-memory set:                                        │  │
│  │  existing_records = {                                         │  │
│  │    ("airtel", "instagram", "airtel"),                         │  │
│  │    ("airtel", "facebook", "airtelindia"),                     │  │
│  │    ("hdfc bank", "instagram", "hdfcbank"),                    │  │
│  │    ...                                                         │  │
│  │  }                                                             │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  DURING SCRAPING:                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  New account found:                                           │  │
│  │  CSE: "Airtel"                                                │  │
│  │  Platform: "instagram"                                        │  │
│  │  Username: "airtel"                                           │  │
│  │                                                                │  │
│  │  Check: ("airtel", "instagram", "airtel") in existing_records?│  │
│  │  ├─ YES → ❌ DUPLICATE (skip, log)                           │  │
│  │  └─ NO  → ✅ NEW (write to CSV, add to set)                  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  RESULT:                                                             │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  ✅ No duplicate rows in full_output.csv                      │  │
│  │  ✅ No need for separate clean_duplicates.py step             │  │
│  │  ✅ Memory efficient (only stores keys, not full rows)        │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Data Flow Comparison

### Current Workflow
```
brand_map.csv (11 CSEs)
    │
    ├─► batch_scraper.py
    │   ├─ Instagram: 50 accounts
    │   └─ Facebook: 120 accounts
    │   Time: 5-10 min
    │
    ├─► main_linkedin.py --batch
    │   └─ LinkedIn: 60 accounts
    │   Time: 10-15 min
    │
    ├─► main_x.py --batch
    │   └─ X: 20 accounts
    │   Time: 15-20 min
    │
    ▼
full_output.csv (250 accounts + duplicates)
    │
    ├─► clean_duplicates.py
    │   └─ Remove 50 duplicates
    │   Time: 1-2 sec
    │
    ▼
full_output.csv (200 accounts, raw)
    │
    ├─► process_results.py
    │   ├─ Remove duplicates
    │   └─ Flag false positives
    │   Time: 2-3 sec
    │
    ▼
full_output_cleaned.csv (200 accounts, clean + flagged)

TOTAL TIME: 30-45 minutes
MANUAL STEPS: 5
```

### Streamlined Workflow
```
brand_map.csv (11 CSEs)
    │
    ├─► unified_scraper.py
    │   ├─ Instagram: 50 accounts  ┐
    │   ├─ Facebook: 120 accounts  ├─ All in parallel
    │   ├─ LinkedIn: 60 accounts   │  Real-time dedup
    │   └─ X: 20 accounts          ┘
    │   Time: 10-15 min
    │
    ▼
full_output.csv (200 accounts, raw)
    │
    ├─► process_results.py
    │   ├─ Remove duplicates
    │   └─ Flag false positives
    │   Time: 2-3 sec
    │
    ▼
full_output_cleaned.csv (200 accounts, clean + flagged)

TOTAL TIME: 10-15 minutes
MANUAL STEPS: 2
```

---

## 🚀 Command Comparison

### Current (5 commands)
```bash
# Step 1: Instagram + Facebook
python batch_scraper.py brand_map.csv temp1.csv --headless

# Step 2: LinkedIn
python main_linkedin.py --batch brand_map.csv --csv-output temp2.csv --headless

# Step 3: X/Twitter
python main_x.py --batch brand_map.csv --csv-output temp3.csv --headless

# Step 4: Merge and deduplicate
cat temp1.csv temp2.csv temp3.csv > full_output.csv
python clean_duplicates.py

# Step 5: Process results (clean + flag)
python process_results.py full_output.csv
```

### Streamlined (2 commands)
```bash
# Step 1: Scrape all platforms
python unified_scraper.py brand_map.csv full_output.csv --headless

# Step 2: Process results (clean + flag)
python process_results.py full_output.csv
```

---

## 📈 Performance Metrics

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PERFORMANCE COMPARISON                            │
├─────────────────────────────────────────────────────────────────────┤
│ Metric              │ Current Workflow │ Streamlined Workflow       │
├─────────────────────────────────────────────────────────────────────┤
│ Total Time          │ 30-45 minutes    │ 10-15 minutes ⚡          │
│ Manual Steps        │ 5 commands       │ 2 commands ✅             │
│ Deduplication       │ Separate step    │ Real-time ⚡              │
│ Resume Capability   │ Partial          │ Full ✅                   │
│ Error Recovery      │ Manual           │ Automatic ✅              │
│ Progress Tracking   │ Per-script       │ Unified ✅                │
│ Parallelism         │ Sequential       │ True parallel ⚡          │
│ Memory Usage        │ High (3x data)   │ Low (dedup set only) ✅   │
│ Disk I/O            │ Multiple writes  │ Single append ✅          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🎉 Summary

### Key Improvements
1. ✅ **50-70% faster** - True parallelism across platforms
2. ✅ **60% fewer steps** - 2 commands instead of 5
3. ✅ **Real-time deduplication** - No separate cleanup needed
4. ✅ **Better error handling** - Automatic retry and recovery
5. ✅ **Unified progress tracking** - Single source of truth
6. ✅ **Resume capability** - Pick up where you left off

### Files Needed
- ✅ `unified_scraper.py` (NEW - to be created)
- ✅ `process_results.py` (KEEP - unified processing)
- ✅ `brand_map.csv` (INPUT)
- ✅ `full_output.csv` (OUTPUT)
- ✅ `flagged_output.csv` (FINAL OUTPUT)

### Files to Archive
- 🗑️ `batch_scraper.py`
- 🗑️ `main_linkedin.py`
- 🗑️ `main_x.py`
- 🗑️ `clean_duplicates.py`
- 🗑️ `batch_scraper_incremental.py`

---

**Ready to implement unified_scraper.py?** 🚀
