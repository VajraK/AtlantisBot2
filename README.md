Atlantis Bot 2

This project is a Google search scraper built using **Node.js (Puppeteer)** and controlled via a **Python** interface.  
It supports stealth mode to bypass bot detection, solves Google reCAPTCHA challenges via 2Captcha, and saves HTML results for each page.

---

## Features

- Headless browser scraping with Puppeteer + stealth plugin
- Automated reCAPTCHA solving with 2Captcha integration
- Configurable maximum pages to scrape (`pages_limit`)
- Saves raw HTML pages locally
- Controlled asynchronously from Python (via subprocess and JSON communication)
- CAPTCHA detection and retries
- Cookie consent handling

---

## Requirements

### Python dependencies

```bash
pip install -r requirements.txt
Node.js dependencies
bash
Copy
Edit
npm install puppeteer-extra puppeteer-extra-plugin-stealth puppeteer-extra-plugin-recaptcha readline js-yaml axios
Configuration
Edit config.yaml to set values such as:

yaml
Copy
Edit
twoCaptchaApiKey: "YOUR_2CAPTCHA_API_KEY"
maxPages: 3
twoCaptchaApiKey — your 2Captcha API key for CAPTCHA solving

maxPages — default max number of Google result pages to scrape (overridden if pages_limit provided in input)

Usage
Python script example
python
Copy
Edit
import asyncio
import json
import subprocess
import sys

async def scrape(query, pages_limit=3):
    input_data = json.dumps({"query": query, "pages_limit": pages_limit})
    proc = await asyncio.create_subprocess_exec(
        "node", "google_scraper.js",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = await proc.communicate(input_data.encode())
    if proc.returncode != 0:
        raise RuntimeError(f"Scraper failed: {stderr.decode().strip()}")
    result = json.loads(stdout.decode())
    if not result.get("success"):
        raise RuntimeError("Scraper error: " + result.get("error", "Unknown error"))
    return result["results"]

# Example usage
asyncio.run(scrape("openAI GPT", pages_limit=5))
Running the scraper standalone
You can also run the scraper directly via Node.js, providing JSON input through stdin:

bash
Copy
Edit
echo '{"query": "openAI GPT", "pages_limit": 5}' | node google_scraper.js
Output
HTML files of Google search results are saved under ./pages/<timestamp>/

File names are google-results-page-1.html, google-results-page-2.html, etc.

Screenshots saved in case of CAPTCHA failures or errors for debugging

Notes
Puppeteer runs headless by default but includes stealth plugins to minimize detection.

2Captcha API key is required for solving Google reCAPTCHA challenges.

The Python script communicates with Node.js scraper via JSON over stdin/stdout.

Adjust pages_limit to control how many pages to scrape per query.

License
MIT License

<3
```
