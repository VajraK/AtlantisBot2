import yaml
import os
import asyncio
import json
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from google_scraper import scrape_google_links
from extract_google_results import extract_all_results
from ai_api import rate_entries_with_gpt
from pdf_work import download_pdfs_from_ready_candidates, convert_pdfs_to_text

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers:
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    file_handler = RotatingFileHandler(
        "main.log", maxBytes=5_000_000, backupCount=5, encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)


def load_config(path="config.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def get_latest_pages_folder(base_folder="pages"):
    if not os.path.isdir(base_folder):
        return None

    subfolders = [f.path for f in os.scandir(base_folder) if f.is_dir()]
    if not subfolders:
        return base_folder

    def parse_folder_name(folder_path):
        try:
            folder_name = os.path.basename(folder_path)
            return datetime.strptime(folder_name, "%Y-%m-%dT%H-%M-%S")
        except Exception:
            return None

    dated_folders = [(folder, parse_folder_name(folder)) for folder in subfolders]
    dated_folders = [(f, d) for f, d in dated_folders if d is not None]

    if not dated_folders:
        return base_folder

    dated_folders.sort(key=lambda x: x[1], reverse=True)
    return dated_folders[0][0]

def save_ready_candidates(combined_results_path, ratings_path, output_path):
    # Load combined results
    with open(combined_results_path, "r", encoding="utf-8") as f:
        combined_results = json.load(f)
    
    # Load ratings
    with open(ratings_path, "r", encoding="utf-8") as f:
        ratings = json.load(f)
    
    # Filter combined results to only those with "YES" rating
    ready_candidates = [
        entry for entry in combined_results
        if ratings.get(entry.get("hash")) == "YES"
    ]
    
    # Save filtered results
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(ready_candidates, f, indent=2, ensure_ascii=False)
    
    logger.info(f"✅ Saved {len(ready_candidates)} ready candidates to {output_path}")

async def async_main():
    config = load_config()
    queries = config.get("google", {}).get("queries")

    if not queries:
        default_query = config.get("google", {}).get(
            "query", 'site:*.com filetype:pdf investment memo'
        )
        queries = [default_query]

    logger.info(f"🔍 Running Google search for queries: {queries}")

    all_paths = []
    pages_limit = config.get("google", {}).get("pages_limit", 1)

    for query in queries:
        logger.info(f"\n🔍 Searching Google for: '{query}'")
        try:
            html_files = await scrape_google_links(query=query, pages_limit=pages_limit)
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

    # Get latest folder where HTMLs were saved
    latest_folder = get_latest_pages_folder("pages")
    if not latest_folder:
        logger.error("❌ Could not find any pages folder to extract results from.")
        return

    logger.info(f"🗂️ Extracting results from latest folder: {latest_folder}")

    # Extract results
    combined_json_path = os.path.join(latest_folder, "combined_results.json")
    extracted = extract_all_results(
        html_folder=latest_folder,
        output_file=combined_json_path,
        output_format='json'
    )
    logger.info(f"✅ Extracted {len(extracted)} unique results into {combined_json_path}")

    logger.info("🤖 Sending results to OpenAI for investment relevance rating...")
    ratings = await rate_entries_with_gpt(extracted)

    # Save ratings to JSON
    ratings_file = os.path.join(latest_folder, "ratings.json")
    with open(ratings_file, "w", encoding="utf-8") as f:
        json.dump(ratings, f, indent=2, ensure_ascii=False)

    logger.info(f"📊 Saved ratings to {ratings_file}")

    # Save ready candidates (only those with YES rating)
    ready_candidates_file = os.path.join(latest_folder, "ready_candidates.json")
    save_ready_candidates(combined_json_path, ratings_file, ready_candidates_file)

    # Download PDFs from ready_candidates.json
    await download_pdfs_from_ready_candidates(ready_candidates_file, base_pages_folder="pages")

    # Convert downloaded PDFs to TXT
    convert_pdfs_to_text(base_folder=latest_folder)

def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
