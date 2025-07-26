import os
import json
import logging
import aiohttp
import asyncio
import async_timeout
import traceback
from pathlib import Path
from pdfminer.high_level import extract_text

logger = logging.getLogger(__name__)

async def download_pdf(session, url, save_path, timeout_secs=20):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36"
        ),
        "Accept": "application/pdf",
        "Referer": url
    }

    try:
        async with async_timeout.timeout(timeout_secs):
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    with open(save_path, "wb") as f:
                        f.write(content)
                    logger.info(f"✅ Downloaded PDF: {save_path}")
                else:
                    logger.error(f"❌ Failed to download {url}, HTTP status: {resp.status}")
    except asyncio.TimeoutError:
        logger.error(f"⏱️ Timeout when downloading {url}")
    except Exception as e:
        logger.error(f"❌ Error downloading {url}: {repr(e)}\n{traceback.format_exc()}")

async def download_pdfs_from_ready_candidates(ready_candidates_path, base_pages_folder="pages"):
    # Load ready candidates
    with open(ready_candidates_path, "r", encoding="utf-8") as f:
        candidates = json.load(f)

    # Filter PDFs
    pdf_candidates = [c for c in candidates if c.get("url", "").lower().endswith(".pdf")]
    if not pdf_candidates:
        logger.info("ℹ️ No PDF URLs found in ready_candidates.json")
        return

    latest_folder = os.path.dirname(ready_candidates_path)
    pdf_folder = os.path.join(latest_folder, "pdf")
    os.makedirs(pdf_folder, exist_ok=True)

    async with aiohttp.ClientSession() as session:
        tasks = []
        for entry in pdf_candidates:
            url = entry["url"]
            filename = f"{entry['hash']}.pdf"
            save_path = os.path.join(pdf_folder, filename)
            tasks.append(download_pdf(session, url, save_path))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"⚠️ Download task {i} raised an exception: {repr(result)}")

    logger.info(f"📥 Attempted to download {len(pdf_candidates)} PDFs into {pdf_folder}")

def convert_pdfs_to_text(base_folder):
    pdf_folder = os.path.join(base_folder, "pdf")
    txt_folder = os.path.join(base_folder, "txt")
    os.makedirs(txt_folder, exist_ok=True)

    pdf_files = list(Path(pdf_folder).glob("*.pdf"))
    if not pdf_files:
        logger.info("ℹ️ No PDFs found to convert.")
        return

    for pdf_file in pdf_files:
        try:
            text = extract_text(str(pdf_file))
            txt_path = os.path.join(txt_folder, f"{pdf_file.stem}.txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(text)
            logger.info(f"📝 Converted {pdf_file.name} to text.")
        except Exception as e:
            logger.error(f"❌ Error converting {pdf_file.name} to text: {repr(e)}\n{traceback.format_exc()}")
