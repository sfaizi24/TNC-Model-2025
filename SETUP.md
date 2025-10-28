# Setup Guide

## Initial Setup

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Playwright Browser (Required for FanDuel)

This is a critical step that's easy to miss!

```bash
playwright install chromium
```

This downloads the Chromium browser that Playwright uses to scrape FanDuel.

### 3. Verify Installation

Run the test suite to make sure everything is working:

```bash
python test_scrapers.py
```

This will test both scrapers and show you what's in your database.

## Running the Scrapers

### Option 1: Run All Sources

```bash
python main.py --week "Week 8" --source all
```

### Option 2: Run Individual Sources

```bash
# First Down Studio
python main.py --week "Week 8" --source firstdown.studio

# FanDuel
python main.py --week "Week 8" --source fanduel.com

# Sleeper
python main.py --week "Week 9" --source sleeper.com --season 2024

# FantasyPros
python main.py --week "Week 8" --source fantasypros.com
```

## Troubleshooting

### FanDuel Scraper Not Working?

**Problem:** No FanDuel projections in database

**Solutions:**
1. Make sure you installed Playwright browsers:
   ```bash
   playwright install chromium
   ```

2. Check if you specified the correct source:
   ```bash
   python main.py --source fanduel.com
   # OR
   python main.py --source all
   ```

3. Run with visible browser to see what's happening:
   ```bash
   python main.py --source fanduel.com --show-browser
   ```

4. Run the test script to diagnose:
   ```bash
   python test_scrapers.py
   ```

### First Down Studio Issues?

**Problem:** Chrome/ChromeDriver errors

**Solution:** Make sure Chrome is installed on your system. The ChromeDriver will be managed automatically by Selenium.

### View What's in Database

```bash
python main.py --view --source all
```

## Common Commands

```bash
# Fresh scrape of both sources
python main.py --source all --week "Week 8"

# View what you have
python main.py --view --source all

# Compare projections
python compare_sources.py --week "Week 8"

# Validate data
jupyter notebook data_validation.ipynb

# Test individual scrapers
python test_scrapers.py
```

## Windows-Specific Notes

- Make sure you have Chrome installed
- Playwright may need admin rights to install browsers
- If you get path errors, try running Command Prompt as Administrator when installing Playwright

## Next Steps

After successful setup:
1. Run both scrapers: `python main.py --source all`
2. Validate data: `python test_scrapers.py`
3. Explore data: `jupyter notebook data_validation.ipynb`
4. Compare sources: `python compare_sources.py --week "Week 8"`

