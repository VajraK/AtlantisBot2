import yaml
import os
import asyncio
import json
import logging
from datetime import datetime, date, timedelta
from logging.handlers import RotatingFileHandler

from google_scraper import scrape_google_links  # Import your scraper

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers:
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    # Rotating file log
    file_handler = RotatingFileHandler(
        "main.log", maxBytes=5_000_000, backupCount=5, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Stream log to console
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)


def load_config(path="config.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)

async def async_main():
    config = load_config()
    queries = config.get("google", {}).get("queries")

    if not queries:
        default_query = config.get("google", {}).get("query", "site:*.com filetype:pdf investment memo")
        queries = [default_query]

    logger.info(f"🔍 Running Google search for queries: {queries}")

    all_paths = []

    for query in queries:
        logger.info(f"\n🔍 Searching Google for: '{query}'")
        try:
            html_files = await scrape_google_links(query=query)
            if html_files:
                all_paths.extend(html_files)
                logger.info(f"✅ Saved {len(html_files)} HTML page(s)")
            else:
                logger.info(f"❌ No pages saved for query: '{query}'")
        except Exception as e:
            logger.error(f"❌ Error running query '{query}': {e}")

    unique_paths = list(set(all_paths))
    if not unique_paths:
        logger.info("ℹ️ No new HTML files generated.")
        return

    logger.info(f"🆕 {len(unique_paths)} unique file(s) saved:")
    for path in unique_paths:
        logger.info(f" - {path}")

def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
