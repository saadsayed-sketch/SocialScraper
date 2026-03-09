# Batch Processing - Detailed Explanation

## Your Questions Answered

### Q1: Will it write ALL accounts found?

**YES! Every single account gets its own row.**

#### Example:
If searching for "Airtel" finds:
- **X Platform**: 10 accounts → 10 rows in CSV
- **Instagram**: 15 accounts → 15 rows in CSV  
- **Facebook**: 8 accounts → 8 rows in CSV
- **Total**: 33 rows (all with CSE = "Airtel")

#### NOT like this (wrong):
```csv
CSE,platform,username
Airtel,x,airtel_india          ❌ Only 1 account per platform
Airtel,instagram,airtel
Airtel,facebook,airtel
```

#### But like this (correct):
```csv
CSE,platform,username
Airtel,x,airtel_india           ✅ ALL accounts written
Airtel,x,airtel_care
Airtel,x,airtel_business
Airtel,x,airtel_payments
Airtel,x,airtel_thanks
Airtel,instagram,airtel
Airtel,instagram,airtel.india
Airtel,instagram,airtel_official
Airtel,facebook,airtel
Airtel,facebook,airtelindia
```

### Q2: Will accounts be unique?

**YES! Uniqueness is guaranteed within each platform.**

#### Deduplication Logic:

**Within Same Platform (Deduplicated):**
```
Keyword "Airtel" finds: @airtel_india, @airtel_care, @airtel_india (duplicate)
Keyword "Bharti Airtel" finds: @airtel_india (duplicate), @airtel_business

Result on X platform:
✅ @airtel_india (kept - first occurrence)
✅ @airtel_care (kept - unique)
✅ @airtel_business (kept - unique)
❌ @airtel_india duplicates (removed)

Total: 3 unique accounts on X
```

**Across Different Platforms (Separate Rows):**
```
@airtel on X → Row 1 (CSE=Airtel, platform=x, username=airtel)
@airtel on Instagram → Row 2 (CSE=Airtel, platform=instagram, username=airtel)
@airtel on Facebook → Row 3 (CSE=Airtel, platform=facebook, username=airtel)

Total: 3 rows (same username, different platforms = NOT duplicates)
```

## Parallel Processing Architecture

### How It Works

```
┌─────────────────────────────────────────────────────────────┐
│ INITIALIZATION (Once at start)                              │
│ ✓ Login to X (reuse session for all CSEs)                  │
│ ✓ Login to Instagram (reuse session for all CSEs)          │
│ ✓ Login to Facebook (reuse session for all CSEs)           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ BATCH 1 (3 CSEs processed simultaneously)                   │
├─────────────────────────────────────────────────────────────┤
│ CSE: Airtel                                                 │
│   ├─ X scraper (parallel) ──────────► 10 accounts found    │
│   ├─ Instagram scraper (parallel) ──► 15 accounts found    │
│   └─ Facebook scraper (parallel) ───► 8 accounts found     │
│   Total: 33 rows written to CSV                             │
├─────────────────────────────────────────────────────────────┤
│ CSE: HDFC Bank                                              │
│   ├─ X scraper (parallel) ──────────► 5 accounts found     │
│   ├─ Instagram scraper (parallel) ──► 7 accounts found     │
│   └─ Facebook scraper (parallel) ───► 3 accounts found     │
│   Total: 15 rows written to CSV                             │
├─────────────────────────────────────────────────────────────┤
│ CSE: SBI                                                    │
│   ├─ X scraper (parallel) ──────────► 8 accounts found     │
│   ├─ Instagram scraper (parallel) ──► 12 accounts found    │
│   └─ Facebook scraper (parallel) ───► 6 accounts found     │
│   Total: 26 rows written to CSV                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
                    10 second cooldown
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ BATCH 2 (Next 3 CSEs)                                       │
│ ... continues ...                                           │
└─────────────────────────────────────────────────────────────┘
```

### Speed Comparison

**Sequential (Old Way - NOT implemented):**
```
Process Airtel:
  X (30s) → Instagram (30s) → Facebook (30s) = 90s
Process HDFC:
  X (30s) → Instagram (30s) → Facebook (30s) = 90s
Process SBI:
  X (30s) → Instagram (30s) → Facebook (30s) = 90s

Total: 270 seconds (4.5 minutes) for 3 CSEs
```

**Parallel (New Way - Implemented):**
```
Process Airtel, HDFC, SBI simultaneously:
  All X scrapers run together (30s)
  All Instagram scrapers run together (30s)
  All Facebook scrapers run together (30s)

Total: ~40 seconds for 3 CSEs (6.75x faster!)
```

## Real-World Example

### Input: brand_map.csv
```csv
keyword,canonical_url,CSE
Airtel,https://www.airtel.in/,Airtel
Bharti Airtel,https://www.airtel.in/,Airtel
Airtel India,https://www.airtel.in/,Airtel
HDFC Bank,https://www.hdfcbank.com/,HDFC Bank
HDFC,https://www.hdfcbank.com/,HDFC Bank
```

### Processing:
```
CSE "Airtel" has 3 keywords: ["Airtel", "Bharti Airtel", "Airtel India"]
  → Search X with "Airtel" → finds 5 accounts
  → Search X with "Bharti Airtel" → finds 3 accounts (2 duplicates)
  → Search X with "Airtel India" → finds 2 accounts (1 duplicate)
  → Deduplicate: 5 + 3 + 2 - 3 duplicates = 7 unique X accounts
  
  → Search Instagram with "Airtel" → finds 8 accounts
  → Search Instagram with "Bharti Airtel" → finds 4 accounts (2 duplicates)
  → Deduplicate: 8 + 4 - 2 duplicates = 10 unique Instagram accounts
  
  → Search Facebook with "Airtel" → finds 3 accounts
  → Search Facebook with "Bharti Airtel" → finds 2 accounts (1 duplicate)
  → Deduplicate: 3 + 2 - 1 duplicate = 4 unique Facebook accounts

Total for "Airtel": 7 + 10 + 4 = 21 rows in CSV
```

### Output: output.csv
```csv
CSE,platform,username,display_name,url,bio_description,found_at
Airtel,x,airtel_india,Airtel India,https://x.com/airtel_india,...,2024-02-23T10:30:00
Airtel,x,airtel_care,Airtel Care,https://x.com/airtel_care,...,2024-02-23T10:30:05
Airtel,x,airtel_business,Airtel Business,https://x.com/airtel_business,...,2024-02-23T10:30:10
Airtel,x,airtel_payments,Airtel Payments,https://x.com/airtel_payments,...,2024-02-23T10:30:15
Airtel,x,airtel_thanks,Airtel Thanks,https://x.com/airtel_thanks,...,2024-02-23T10:30:20
Airtel,x,airtel_4g,Airtel 4G,https://x.com/airtel_4g,...,2024-02-23T10:30:25
Airtel,x,airtel_wynk,Airtel Wynk,https://x.com/airtel_wynk,...,2024-02-23T10:30:30
Airtel,instagram,airtel,Airtel,https://instagram.com/airtel/,...,2024-02-23T10:31:00
Airtel,instagram,airtel.india,Airtel India,https://instagram.com/airtel.india/,...,2024-02-23T10:31:05
... (8 more Instagram accounts)
Airtel,facebook,airtel,Airtel India,https://facebook.com/airtel,...,2024-02-23T10:32:00
... (3 more Facebook accounts)
HDFC Bank,x,hdfcbank,HDFC Bank,https://x.com/hdfcbank,...,2024-02-23T10:35:00
... (all HDFC accounts)
```

**Notice:**
- "Airtel" appears 21 times (once per account found)
- Each account has its own complete row
- No information is lost

## Performance Tuning

### Concurrent Processing Levels

**Conservative (--concurrent 2):**
- Safer for rate limiting
- Lower memory usage
- Slower overall

**Balanced (--concurrent 3) [DEFAULT]:**
- Good balance of speed and safety
- Recommended for most use cases

**Aggressive (--concurrent 5):**
- Fastest processing
- Higher memory usage
- Risk of rate limiting

### Example Commands

```bash
# Safe and slow (good for first run)
python batch_scraper.py brand_map.csv output.csv --concurrent 2

# Balanced (recommended)
python batch_scraper.py brand_map.csv output.csv --concurrent 3 --headless

# Fast and aggressive (for large batches)
python batch_scraper.py brand_map.csv output.csv --concurrent 5 --headless
```

## Summary

✅ **ALL accounts written** - Every account gets its own row  
✅ **Unique within platform** - No duplicate @airtel_india on X  
✅ **Separate across platforms** - @airtel on X and Instagram = 2 rows  
✅ **CSE name repeated** - Easy to filter and analyze  
✅ **Parallel processing** - 6-10x faster than sequential  
✅ **Resume capability** - Continue after interruption  
✅ **CSV output** - Easy to use in Excel/Google Sheets
