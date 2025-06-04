import asyncio
from data_pipeline.downloader import download_recent_data, cleanup_old_raw_data, download_daily_data
from data_pipeline.processor import process_all_new_data
from data_pipeline.db_setup import setup_database

async def main_pipeline_job(days_to_fetch=3):
    print("Starting data pipeline job...")

    # 1. Ensure database schema is up to date
    print("\nStep 1: Setting up database...")
    await setup_database()

    # 2. Download recent data
    print(f"\nStep 2: Downloading data for the last {days_to_fetch} day(s)...")
    # Option 1: Fetch for a range of past days
    # await download_recent_data(num_days=days_to_fetch) 
    # Option 2: Fetch only for yesterday (more common for a daily job)
    await download_daily_data(days_ago=1) 
    # You might want to fetch for today as well, but data might be incomplete
    # await download_daily_data(days_ago=0)

    # 3. Process downloaded data
    print("\nStep 3: Processing downloaded data...")
    await process_all_new_data()

    # 4. Cleanup old raw files
    print("\nStep 4: Cleaning up old raw data files...")
    cleanup_old_raw_data() # Synchronous, but quick

    print("\nData pipeline job finished.")

if __name__ == "__main__":
    # Run the pipeline for the last 1 day (i.e., yesterday's data)
    # Adjust days_to_fetch as needed for initial population or catch-up
    asyncio.run(main_pipeline_job(days_to_fetch=1))