import asyncio
import json

async def scrape_google_links(query: str):
    input_data = {"query": query}
    input_json = json.dumps(input_data)

    proc = await asyncio.create_subprocess_exec(
        "node", "google_scraper.js",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await proc.communicate(input_json.encode())

    if proc.returncode != 0:
        raise RuntimeError(f"Google scraper failed: {stderr.decode().strip()}")

    try:
        output = json.loads(stdout.decode())
        if not output.get("success"):
            raise RuntimeError("Scraper returned unsuccessful result")
        return output["results"]  # list of saved file paths
    except json.JSONDecodeError:
        raise RuntimeError("Failed to parse Google scraper output")
