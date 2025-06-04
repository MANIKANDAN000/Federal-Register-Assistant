import asyncio
import aiohttp
import aiofiles
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# Create directories if they don't exist
Path("data/raw").mkdir(parents=True, exist_ok=True)
Path("data/processed").mkdir(parents=True, exist_ok=True)


RAW_DATA_DIR = Path("data/raw")
PROCESSED_DATA_DIR = Path("data/processed") # Not used in this script, but good for organization
FEDERAL_REGISTER_API_URL = "https://www.federalregister.gov/api/v1/documents.json"

# Keep raw data files for N days (example, configurable via .env)
RAW_DATA_RETENTION_DAYS = int(os.getenv("RAW_DATA_RETENTION_DAYS", 7))


async def fetch_documents(session, params):
    try:
        async with session.get(FEDERAL_REGISTER_API_URL, params=params) as response:
            response.raise_for_status() # Raise an exception for HTTP errors
            data = await response.json()
            return data.get("results", [])
    except aiohttp.ClientError as e:
        print(f"Error fetching data with params {params}: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON with params {params}: {e}")
        return []


async def download_daily_data(days_ago=1, per_page=200):
    """
    Downloads data for a specific day (days_ago from today).
    The API can be slow or return partial results for "today", so often 1 day ago is more reliable.
    Fetches documents published on a specific date.
    """
    target_date = datetime.now() - timedelta(days=days_ago)
    date_str = target_date.strftime("%Y-%m-%d")
    
    print(f"Fetching documents for publication date: {date_str}")

    all_documents = []
    page = 1
    
    async with aiohttp.ClientSession() as session:
        while True:
            params = {
                "conditions[publication_date][is]": date_str,
                "per_page": per_page,
                "page": page,
                "fields[]": [ # Request specific fields to keep payload smaller
                    "document_number", "title", "publication_date", 
                    "type", "abstract", "html_url", "raw_text_url" # raw_text_url might be useful
                ]
            }
            print(f"Fetching page {page} for {date_str}...")
            documents_page = await fetch_documents(session, params)
            
            if not documents_page:
                print(f"No more documents found for {date_str} on page {page} or error occurred.")
                break
            
            all_documents.extend(documents_page)
            
            # The API doesn't clearly state total pages, so we fetch until an empty page is returned.
            # Or, if using the `count` and `total_pages` from the response metadata (if reliable).
            # For this API, if `len(documents_page) < per_page`, it's likely the last page.
            if len(documents_page) < per_page:
                print(f"Fetched {len(documents_page)} documents, likely last page for {date_str}.")
                break
            page += 1
            await asyncio.sleep(0.5) # Be respectful to the API

    if all_documents:
        filename = RAW_DATA_DIR / f"federal_register_{date_str}.json"
        async with aiofiles.open(filename, "w") as f:
            await f.write(json.dumps(all_documents, indent=2))
        print(f"Successfully downloaded {len(all_documents)} documents for {date_str} to {filename}")
        return str(filename)
    else:
        print(f"No documents found or downloaded for {date_str}.")
        return None


async def download_recent_data(num_days=7):
    """Downloads data for the past num_days."""
    downloaded_files = []
    for i in range(1, num_days + 1): # Start from 1 day ago up to num_days ago
        print(f"\n--- Downloading data for {i} day(s) ago ---")
        file_path = await download_daily_data(days_ago=i)
        if file_path:
            downloaded_files.append(file_path)
        await asyncio.sleep(1) # Small delay between fetching different days
    return downloaded_files


def cleanup_old_raw_data():
    """Removes raw data files older than RAW_DATA_RETENTION_DAYS."""
    now = datetime.now()
    for filename in RAW_DATA_DIR.glob("*.json"):
        try:
            # Assuming filename format like federal_register_YYYY-MM-DD.json
            date_str = filename.stem.split("_")[-1]
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            if (now - file_date).days > RAW_DATA_RETENTION_DAYS:
                print(f"Cleaning up old raw data file: {filename}")
                os.remove(filename)
        except (ValueError, IndexError) as e:
            print(f"Could not parse date from filename {filename}: {e}. Skipping cleanup for this file.")


if __name__ == "__main__":
    # Example usage: download data for the last 3 days
    # asyncio.run(download_recent_data(num_days=3))
    # cleanup_old_raw_data()
    # For a single day (yesterday)
    asyncio.run(download_daily_data(days_ago=1))
    cleanup_old_raw_data()