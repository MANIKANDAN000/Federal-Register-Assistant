import asyncio
import aiomysql
import aiofiles
import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

RAW_DATA_DIR = Path("data/raw")
PROCESSED_DATA_DIR = Path("data/processed") # To move files after processing

async def get_db_pool():
    return await aiomysql.create_pool(
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        db=os.getenv("MYSQL_DB"),
        autocommit=False # We'll manage transactions
    )

async def process_file(filepath: Path, pool):
    print(f"Processing file: {filepath.name}")
    try:
        async with aiofiles.open(filepath, "r") as f:
            content = await f.read()
            documents = json.loads(content)
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {filepath.name}. Skipping.")
        return 0
    except Exception as e:
        print(f"Error reading file {filepath.name}: {e}. Skipping.")
        return 0

    if not isinstance(documents, list):
        print(f"Expected a list of documents in {filepath.name}, got {type(documents)}. Skipping.")
        return 0

    processed_count = 0
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            for doc in documents:
                if not isinstance(doc, dict) or "document_number" not in doc:
                    print(f"Skipping invalid document structure in {filepath.name}: {str(doc)[:100]}")
                    continue
                
                # Ensure abstract is a string, can be None or missing
                abstract_text = doc.get("abstract")
                if isinstance(abstract_text, dict) and "abstract" in abstract_text: # Sometimes it's nested
                    abstract_text = abstract_text.get("abstract")
                elif not isinstance(abstract_text, str) and abstract_text is not None:
                    abstract_text = str(abstract_text) # Fallback if it's some other type

                try:
                    await cur.execute(
                        """
                        INSERT INTO federal_documents (
                            document_number, title, publication_date, document_type, 
                            abstract, html_url, raw_data
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            title = VALUES(title),
                            publication_date = VALUES(publication_date),
                            document_type = VALUES(document_type),
                            abstract = VALUES(abstract),
                            html_url = VALUES(html_url),
                            raw_data = VALUES(raw_data),
                            updated_at = CURRENT_TIMESTAMP;
                        """,
                        (
                            doc.get("document_number"),
                            doc.get("title"),
                            doc.get("publication_date"), # Assumes YYYY-MM-DD format
                            doc.get("type"),
                            abstract_text,
                            doc.get("html_url"),
                            json.dumps(doc) # Store the whole original doc as JSON
                        )
                    )
                    processed_count += 1
                except aiomysql.MySQLError as e:
                    print(f"DB Error processing document {doc.get('document_number')}: {e}")
                except Exception as e:
                    print(f"Generic error processing document {doc.get('document_number')}: {e}")
            try:
                await conn.commit()
                print(f"Committed {processed_count} documents from {filepath.name} to DB.")
            except aiomysql.MySQLError as e:
                print(f"Commit error for {filepath.name}: {e}")
                await conn.rollback()


    # Move processed file (optional, good practice)
    try:
        PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
        destination = PROCESSED_DATA_DIR / filepath.name
        # Ensure we don't overwrite if running multiple times on same day before cleanup
        if destination.exists(): 
            # Add a timestamp or counter if needed, or just overwrite for this demo
            print(f"Processed file {destination.name} already exists. Overwriting.")
        os.rename(filepath, destination) 
        print(f"Moved {filepath.name} to {PROCESSED_DATA_DIR}")
    except Exception as e:
        print(f"Error moving file {filepath.name} to processed directory: {e}")
        # If moving fails, we might reprocess. Consider how to handle this.
        # For demo, just print.

    return processed_count


async def process_all_new_data():
    pool = await get_db_pool()
    total_docs_processed = 0
    
    raw_files = list(RAW_DATA_DIR.glob("*.json"))
    if not raw_files:
        print("No raw data files found to process.")
    else:
        print(f"Found {len(raw_files)} raw files to process.")

    for filepath in raw_files:
        count = await process_file(filepath, pool)
        total_docs_processed += count
    
    print(f"\nTotal documents processed in this run: {total_docs_processed}")
    
    pool.close()
    await pool.wait_closed()


if __name__ == "__main__":
    asyncio.run(process_all_new_data())