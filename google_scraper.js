const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const RecaptchaPlugin = require('puppeteer-extra-plugin-recaptcha');
const readline = require('readline');
const fs = require('fs');
const yaml = require('js-yaml');
const path = require('path');

const config = yaml.load(fs.readFileSync('./config.yaml', 'utf8'));

puppeteer.use(StealthPlugin());
puppeteer.use(
  RecaptchaPlugin({
    provider: {
      id: '2captcha',
      token: config.twoCaptchaApiKey
    },
    visualFeedback: true,
    solveScoreBased: true,
    solveInactiveChallenges: true,
    solveInViewportOnly: false,
    solveTimeout: 120000
  })
);

async function delay(ms, reason = '') {
  if (reason) console.error(`⏳ Waiting ${ms / 1000}s - ${reason}`);
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function scrapeGoogleResults(query) {
  const url = `https://www.google.com/search?q=${encodeURIComponent(query)}`;
  console.error(`🔍 Opening Google Search URL: ${url}`);

  const browser = await puppeteer.launch({
    headless: false,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-blink-features=AutomationControlled',
      '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    ],
    defaultViewport: null,
    slowMo: 50
  });

  const page = await browser.newPage();
  await page.setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36");

  page.setDefaultNavigationTimeout(180000);
  page.setDefaultTimeout(60000);

  const results = [];

  try {
    console.error('🌐 Navigating to Google...');
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 180000 });
    await delay(5000, 'Initial page load');

    // CAPTCHA solving
    let captchaSolved = false;
    for (let attempt = 1; attempt <= 3; attempt++) {
      console.error(`🔒 Attempting to solve CAPTCHAs (attempt ${attempt}/3)...`);
      const { solved, error } = await page.solveRecaptchas().catch(err => ({ solved: [], error: err }));
      
      if (solved?.length > 0) {
        captchaSolved = true;
        console.error(`✅ Solved ${solved.length} CAPTCHA(s)`);
        await delay(10000, 'Waiting after CAPTCHA solution');
        break;
      }
      
      if (attempt < 3) {
        console.error(`⚠️ CAPTCHA solve failed, retrying... (${error?.message || 'unknown error'})`);
        await delay(15000, 'Waiting before retry');
      }
    }

    if (!captchaSolved) {
      console.error('❌ Failed to solve CAPTCHAs after 3 attempts');
      await page.screenshot({ path: 'captcha-failure.png' });
    }

    // 🌐 Handle language + cookie popups
    try {
      console.error('🌍 Checking for language/cookie popups...');
      
      // Click globe (language selection)
      const langButtonSelector = 'div.QS5gu.ud1jmf, div[aria-label*="language"], div[aria-label*="język"]';
      const langButton = await page.$(langButtonSelector);
      if (langButton) {
        await langButton.click();
        console.error('🌐 Clicked language selector');
        await delay(3000);

        // Click "English (United Kingdom)" if found - FIXED here
        await page.evaluate(() => {
          const langOptions = Array.from(document.querySelectorAll('li.Ge0Aub[role="menuitem"]'));
          const enOption = langOptions.find(el => el.getAttribute('aria-label')?.includes('English (United Kingdom)'));
          if (enOption) enOption.click();
        });
        await delay(5000, 'Language changed to English (UK)');
      }

      // Accept cookies in any language
      const acceptSelectors = [
        'div.QS5gu.sy4vM', // Polish
        'div[role="button"]:has-text("Accept all")',
        'div[role="button"]:has-text("Zaakceptuj wszystko")',
        'button:has-text("Accept all")',
        'button:has-text("I agree")',
        'div[role="button"]:has-text("Akceptuję")',
        'button[aria-label="Accept all"]',
      ];

      for (const selector of acceptSelectors) {
        try {
          const btn = await page.$(selector);
          if (btn) {
            await btn.click();
            console.error('🍪 Clicked "Accept all" consent button');
            await delay(3000, 'Waiting after accepting cookies');
            break;
          }
        } catch { }
      }
    } catch (err) {
      console.error('⚠️ Language or consent popup handling failed:', err.message);
    }

    // Time filter
    try {
        console.error('⏱️ Applying time filter...');
        await page.waitForSelector('#hdtb-tls', { timeout: 10000 });
        await page.click('#hdtb-tls');
        await delay(2000, 'Waiting for tools menu');
    
        await page.evaluate(() => {
        const items = Array.from(document.querySelectorAll('div[jsname="qRxief"]'));
        const past24El = items.find(el => {
            const a = el.querySelector('a[href*="tbs=qdr:d"]');
            return a && /past\s*24\s*hours/i.test(a.textContent);
        });
        if (past24El) {
            past24El.querySelector('a[href*="tbs=qdr:d"]').click();
        }
        });
        await delay(8000, 'Waiting for time filter to apply');
    } catch (err) {
        console.error('⚠️ Failed to apply time filter:', err.message);
    }

    // Final CAPTCHA check
    try {
      console.error('🔍 Final CAPTCHA check...');
      const { solved } = await page.solveRecaptchas();
      if (solved?.length > 0) {
        console.error(`✅ Solved additional ${solved.length} CAPTCHA(s)`);
        await delay(10000, 'Waiting after final CAPTCHA');
      }
    } catch (err) {
      console.error('⚠️ Final CAPTCHA check failed:', err.message);
    }
    
    // 💾 Save full HTML
    // Replace the file saving section with this code:
    try {
        const timestamp = new Date().toISOString().split('.')[0].replace(/:/g, '-');
        const folderPath = `./pages/${timestamp}`;
        fs.mkdirSync(folderPath, { recursive: true });
    
        // Create filesystem-safe filename
        const safeFilename = `google-results-${Date.now()}.html`;
        const filePath = `${folderPath}/${safeFilename}`;
    
        const htmlContent = await page.content();
        fs.writeFileSync(filePath, htmlContent, 'utf8');
    
        console.error(`✅ Saved HTML to ${filePath}`);
        results.push(filePath);
    } catch (err) {
        console.error(`❌ Failed to save HTML: ${err.message}`);
    }
    
  } catch (err) {
    console.error(`❌ Critical error during scraping: ${err.message}`);
    await page.screenshot({ path: 'error-screenshot.png' });
  } finally {
    await browser.close();
  }

  return results;
}

// Main logic
async function main() {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false
  });

  let inputData = '';
  for await (const line of rl) {
    inputData += line;
  }

  try {
    const { query } = JSON.parse(inputData);
    const results = await scrapeGoogleResults(query);
    console.log(JSON.stringify({ success: true, results }));
  } catch (err) {
    console.log(JSON.stringify({ success: false, error: err.message }));
    process.exit(1);
  }
}

if (require.main === module) {
  main().catch(err => {
    console.error(err);
    process.exit(1);
  });
}

module.exports = { scrapeGoogleResults };
