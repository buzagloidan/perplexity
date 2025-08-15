# Perplexity Code Tester

Automatically generates and tests random Perplexity promo codes.

## Features
- Generates random codes in format: MEO + 9 random characters (A-Z, 0-9)
- Tests codes in parallel for faster execution
- Bypasses Selenium detection using undetected-chromedriver
- Saves results to timestamped text files
- Runs in headless mode for cloud deployment

## Local Usage
```bash
python perplexity_railway.py
```

## Railway Deployment
1. Connect your GitHub repo to Railway
2. Deploy automatically with the included configuration files

## Configuration
- `NUM_CODES_TO_TEST`: Number of random codes to generate and test (default: 100)
- `MAX_WORKERS`: Number of parallel browser instances (default: 5)

## Output
Results are saved to `perplexity_random_results_TIMESTAMP.txt` with:
- Working codes (if any found)
- Complete test results for all codes
- Timestamp and summary statistics