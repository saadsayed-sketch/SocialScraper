# Process Results Consolidation

## Summary

`flag_false_positives.py` has been removed and its functionality consolidated into `process_results.py`.

## Why the Consolidation?

Previously, we had two separate scripts:
1. `clean_duplicates.py` - Remove duplicate entries
2. `flag_false_positives.py` - Flag false positives based on similarity

This required running multiple commands and managing intermediate files. The new `process_results.py` combines both operations into a single, efficient workflow.

## What Changed?

### Before (2 separate steps)
```bash
# Step 1: Clean duplicates
python clean_duplicates.py full_output.csv

# Step 2: Flag false positives
python flag_false_positives.py --input full_output.csv --output flagged_output.csv
```

### After (1 unified step)
```bash
# Single command does both
python process_results.py full_output.csv
```

## Features of process_results.py

### Deduplication
- Removes duplicates by `username + CSE + platform`
- Removes duplicates by `URL + platform`
- Keeps first occurrence of each unique entry
- Tracks and reports duplicate statistics

### False Positive Detection
- **Verified accounts** - Flags accounts with platform verification
- **Official domains** - Detects official domain URLs from brand_map.csv
- **High similarity** - Flags accounts with >95% similarity to CSE name
- **Celebrity accounts** - Filters known celebrity/popular accounts
- **Exact keyword match** - Flags exact matches with official keywords

### Additional Features
- **Automatic backups** - Creates timestamped backup before processing
- **Detailed statistics** - Shows counts for duplicates and false positives
- **Verbose logging** - Optional detailed output for debugging
- **Brand map integration** - Uses brand_map.csv for official domains/keywords
- **Reason tracking** - Records why each entry was flagged as false positive

## Command Line Options

```bash
# Basic usage (creates full_output_cleaned.csv)
python process_results.py full_output.csv

# Specify output file
python process_results.py full_output.csv --output cleaned_results.csv

# Use custom brand map
python process_results.py full_output.csv --brand-map my_brands.csv

# Skip backup creation
python process_results.py full_output.csv --no-backup

# Quiet mode (less verbose)
python process_results.py full_output.csv --quiet
```

## Output Format

The script adds two columns to the CSV:
- `false_positive` - TRUE/FALSE flag
- `fp_reason` - Reason for flagging (verified_account, official_domain, etc.)

## Example Output

```
📊 PROCESSING RESULTS
======================================================================
Total rows read: 250
Unique entries: 200
Duplicates removed: 50
  - By username+CSE+platform: 30
  - By URL+platform: 20

🚩 False Positives Flagged: 15

  Breakdown by reason:
    - verified_account: 8
    - official_domain: 4
    - celebrity_account: 2
    - high_similarity_to_cse: 1

✅ Final output: 200 entries
======================================================================
```

## Migration Guide

If you have existing scripts or documentation referencing `flag_false_positives.py`:

### Replace this:
```bash
python flag_false_positives.py --input full_output.csv --output flagged_output.csv
```

### With this:
```bash
python process_results.py full_output.csv --output flagged_output.csv
```

### Or simply:
```bash
python process_results.py full_output.csv
```

## Benefits

1. **Fewer commands** - One script instead of two
2. **Faster processing** - Single pass through data
3. **Better false positive detection** - More comprehensive checks
4. **Automatic backups** - Safety before processing
5. **Better reporting** - Detailed statistics and breakdowns
6. **Consistent workflow** - Same script for all platforms

## Files Updated

All documentation has been updated to reference `process_results.py`:
- ✅ STREAMLINED_WORKFLOW.md
- ✅ STREAMLINED_FLOWCHART.md
- ✅ BATCH_MODE_ADDED.md
- ✅ ADVANCED_FEATURES.md

## Backward Compatibility

The output format is compatible with existing workflows. The CSV structure remains the same with the addition of:
- `false_positive` column (TRUE/FALSE)
- `fp_reason` column (reason for flagging)

Existing scripts that read the output CSV will continue to work without modification.
