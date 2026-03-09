# Advanced Features - Unified Scraper

## 🔄 Retry Logic & Graceful Failure Handling

The unified scraper now includes robust error handling and retry mechanisms to ensure maximum reliability.

---

## 🎯 Key Features

### 1. Automatic Retry with Exponential Backoff
- **Platform initialization:** Up to 3 retries (configurable)
- **Scraping operations:** Up to 2 retries per platform
- **Exponential backoff:** 1s, 2s, 4s, 8s...
- **Graceful degradation:** Continues with other platforms if one fails

### 2. Manual Intervention Mode
- **Default manual platforms:** X and LinkedIn (known to need manual login)
- **Visible browser:** Opens browser window for manual interaction
- **Configurable:** Specify which platforms need manual intervention
- **Mixed mode:** Some platforms headless, others visible

### 3. Graceful Failure Handling
- **Platform-level:** If one platform fails, others continue
- **CSE-level:** If one CSE fails, others continue
- **Keyword-level:** If one keyword fails, others continue
- **Detailed logging:** All failures logged with context

---

## 📋 Usage Examples

### Basic Usage (Recommended)

```bash
# Default: X and LinkedIn open visible browsers for manual login
# Instagram and Facebook run headless
python unified_scraper.py brand_map.csv full_output.csv --headless
```

**What happens:**
- Instagram: Headless (fast, automated)
- Facebook: Headless (fast, automated)
- LinkedIn: Visible browser (you can manually log in if needed)
- X: Visible browser (you can manually log in if needed)

---

### All Platforms Headless (Risky)

```bash
# Force all platforms to run headless (may fail on X/LinkedIn)
python unified_scraper.py brand_map.csv full_output.csv --headless --manual-platforms ""
```

**Use when:**
- You have valid persistent sessions for all platforms
- Running on a server without display
- You're confident login won't be required

---

### Custom Manual Platforms

```bash
# Only X needs manual intervention
python unified_scraper.py brand_map.csv full_output.csv --headless --manual-platforms x

# Multiple platforms need manual intervention
python unified_scraper.py brand_map.csv full_output.csv --headless --manual-platforms x,linkedin,instagram
```

**Use when:**
- You know which platforms have session issues
- You want fine-grained control over browser visibility

---

### Adjust Retry Attempts

```bash
# More aggressive retries (5 attempts instead of 3)
python unified_scraper.py brand_map.csv full_output.csv --retries 5

# No retries (fail fast)
python unified_scraper.py brand_map.csv full_output.csv --retries 0
```

**Use when:**
- Network is unstable (increase retries)
- Testing/debugging (decrease retries)

---

## 🔍 How Retry Logic Works

### Platform Initialization Retry

```
Attempt 1: Initialize LinkedIn
├─ Try to log in
└─ ❌ Failed (session expired)

Wait 1 second...

Attempt 2: Initialize LinkedIn
├─ Try to log in
└─ ❌ Failed (bot detection)

Wait 2 seconds...

Attempt 3: Initialize LinkedIn
├─ Try to log in
└─ ❌ Failed (network error)

Wait 4 seconds...

Attempt 4: Initialize LinkedIn
├─ Try to log in
└─ ❌ Failed (max retries reached)

Result: LinkedIn skipped, continue with other platforms
```

### Scraping Operation Retry

```
CSE: Airtel
Platform: Instagram
Keyword: "Airtel"

Attempt 1: Search Instagram
├─ Search for "Airtel"
└─ ❌ Failed (timeout)

Wait 5 seconds...

Attempt 2: Search Instagram
├─ Search for "Airtel"
└─ ✅ Success (found 5 accounts)

Result: 5 accounts collected
```

---

## 🛡️ Graceful Failure Handling

### Scenario 1: One Platform Fails

```
CSE: HDFC Bank
├─ Instagram: ✅ 5 accounts
├─ Facebook: ✅ 12 accounts
├─ LinkedIn: ❌ Failed (login required)
└─ X: ✅ 2 accounts

Result: 19 accounts collected from 3/4 platforms
Status: ✅ Success (partial)
```

### Scenario 2: One Keyword Fails

```
CSE: Airtel
Platform: Instagram
├─ Keyword "Airtel": ✅ 3 accounts
├─ Keyword "Bharti Airtel": ❌ Failed (rate limit)
├─ Keyword "Airtel India": ✅ 2 accounts
└─ Keyword "airtelbank": ✅ 1 account

Result: 6 accounts collected from 3/4 keywords
Status: ✅ Success (partial)
```

### Scenario 3: All Platforms Fail for One CSE

```
CSE: Civil Registration System
├─ Instagram: ❌ Failed (no results)
├─ Facebook: ❌ Failed (no results)
├─ LinkedIn: ❌ Failed (login required)
└─ X: ❌ Failed (bot detection)

Result: 0 accounts collected
Status: ❌ Failed (marked in progress.json)
Next CSE: Continue processing
```

---

## 📊 Progress Tracking

### progress.json Structure

```json
{
  "last_run": "2026-02-25T10:30:00",
  "completed_cses": [
    "Airtel",
    "HDFC Bank",
    "ICICI Bank"
  ],
  "failed_cses": {
    "Civil Registration System": "All platforms failed",
    "NIC": "No platforms initialized"
  },
  "stats": {
    "total_accounts": 250
  }
}
```

### Resume After Failure

```bash
# First run (interrupted after 3 CSEs)
python unified_scraper.py brand_map.csv full_output.csv --headless
# Processed: Airtel, HDFC Bank, ICICI Bank
# Interrupted: Ctrl+C

# Resume (continues from CSE #4)
python unified_scraper.py brand_map.csv full_output.csv --resume --headless
# Skips: Airtel, HDFC Bank, ICICI Bank
# Processes: Bank of Baroda, Punjab National Bank, ...
```

---

## 🎯 Best Practices

### 1. First Run (Manual Intervention)

```bash
# Run without --headless first to manually log in
python unified_scraper.py brand_map.csv full_output.csv

# What to do:
# 1. Wait for browser windows to open
# 2. Manually log in to X and LinkedIn if prompted
# 3. Sessions will be saved for future runs
# 4. Next time you can use --headless
```

### 2. Production Run (Headless with Manual Fallback)

```bash
# Recommended for production
python unified_scraper.py brand_map.csv full_output.csv --headless --retries 5

# What happens:
# - Instagram/Facebook: Fully automated (headless)
# - X/LinkedIn: Visible browser (manual login if needed)
# - 5 retry attempts for transient failures
# - Continues even if some platforms fail
```

### 3. Server/Headless Environment

```bash
# If running on server without display
python unified_scraper.py brand_map.csv full_output.csv --headless --manual-platforms ""

# Prerequisites:
# - Valid persistent sessions for all platforms
# - Or accept that X/LinkedIn may fail
# - Use --resume to retry failed CSEs later
```

### 4. Debugging Mode

```bash
# Run with minimal retries and verbose logging
python unified_scraper.py brand_map.csv full_output.csv --retries 1 --concurrent 1

# What happens:
# - Process one CSE at a time (easier to debug)
# - Fail fast (only 1 retry)
# - All output visible in terminal
```

---

## 🔧 Configuration Options

### Command Line Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--headless` | False | Run browsers in headless mode |
| `--manual-platforms` | `x,linkedin` | Platforms that need manual intervention |
| `--retries` | 3 | Max retry attempts for failed operations |
| `--concurrent` | 3 | Max concurrent CSEs to process |
| `--platforms` | all | Comma-separated list of platforms |
| `--resume` | False | Resume from previous run |

### Examples

```bash
# Conservative (safe, slower)
python unified_scraper.py brand_map.csv full_output.csv \
  --concurrent 1 \
  --retries 5 \
  --manual-platforms x,linkedin

# Aggressive (fast, riskier)
python unified_scraper.py brand_map.csv full_output.csv \
  --headless \
  --concurrent 5 \
  --retries 1 \
  --manual-platforms ""

# Balanced (recommended)
python unified_scraper.py brand_map.csv full_output.csv \
  --headless \
  --concurrent 3 \
  --retries 3 \
  --manual-platforms x,linkedin
```

---

## 📈 Failure Scenarios & Solutions

### Scenario 1: X Login Fails

**Symptom:**
```
❌ X login failed
🔄 Retrying X in 1s... (attempt 1/3)
❌ X login failed
🔄 Retrying X in 2s... (attempt 2/3)
❌ X login failed
❌ X failed after 3 attempts
```

**Solution:**
```bash
# Run without headless for X
python unified_scraper.py brand_map.csv full_output.csv --manual-platforms x

# Or skip X entirely
python unified_scraper.py brand_map.csv full_output.csv --platforms instagram,facebook,linkedin
```

---

### Scenario 2: Rate Limited

**Symptom:**
```
⚠️  instagram: Error searching with 'Airtel': Rate limited
⚠️  instagram: Error searching with 'Bharti Airtel': Rate limited
```

**Solution:**
```bash
# Reduce concurrency and increase retries
python unified_scraper.py brand_map.csv full_output.csv --concurrent 1 --retries 5

# Or wait and resume later
# Wait 15-30 minutes
python unified_scraper.py brand_map.csv full_output.csv --resume
```

---

### Scenario 3: Network Timeout

**Symptom:**
```
❌ linkedin: Scraping error for HDFC Bank: Timeout
🔄 Retrying linkedin for HDFC Bank in 5s...
✅ linkedin: Found 3 unique accounts
```

**Solution:**
- Automatic retry handles this
- If persistent, check network connection
- Increase retry count: `--retries 5`

---

### Scenario 4: All Platforms Fail

**Symptom:**
```
❌ Civil Registration System: All platforms failed
```

**Solution:**
```bash
# Check progress.json for failed CSEs
cat progress.json | grep failed_cses

# Retry only failed CSEs
# 1. Edit brand_map.csv to include only failed CSEs
# 2. Run again
python unified_scraper.py failed_cses.csv full_output.csv --headless

# Or manually investigate the CSE
python unified_scraper.py brand_map.csv test.csv --platforms instagram --concurrent 1
```

---

## 📊 Monitoring & Logs

### Real-time Monitoring

```bash
# Watch log file in real-time
tail -f unified_scraper.log

# Filter for errors only
tail -f unified_scraper.log | grep ERROR

# Filter for specific platform
tail -f unified_scraper.log | grep instagram
```

### Post-run Analysis

```bash
# Count errors by platform
grep ERROR unified_scraper.log | grep -oP '(instagram|facebook|linkedin|x)' | sort | uniq -c

# Find failed CSEs
grep "All platforms failed" unified_scraper.log

# Check retry attempts
grep "Retrying" unified_scraper.log | wc -l
```

---

## 🎉 Summary

### What's New

1. ✅ **Automatic retry** - Up to 3 attempts with exponential backoff
2. ✅ **Manual intervention mode** - Visible browser for X and LinkedIn
3. ✅ **Graceful failure handling** - Continues even if platforms fail
4. ✅ **Per-platform headless control** - Mix headless and visible browsers
5. ✅ **Detailed failure tracking** - Know exactly what failed and why
6. ✅ **Resume capability** - Pick up where you left off

### Recommended Usage

```bash
# First run (establish sessions)
python unified_scraper.py brand_map.csv full_output.csv

# Subsequent runs (fully automated)
python unified_scraper.py brand_map.csv full_output.csv --headless

# Process results (clean + flag)
python process_results.py full_output.csv
```

### Key Benefits

- **Reliability:** Automatic retries handle transient failures
- **Flexibility:** Manual intervention when needed
- **Resilience:** Continues processing even if some platforms fail
- **Transparency:** Detailed logging of all failures
- **Efficiency:** Parallel processing with graceful degradation

---

**Your scraper is now production-ready with enterprise-grade error handling!** 🚀
