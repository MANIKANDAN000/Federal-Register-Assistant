import asyncio
import aiomysql
import os
from dotenv import load_dotenv

load_dotenv()

async def get_db_pool():
    return await aiomysql.create_pool(
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        db=os.getenv("MYSQL_DB"),
        autocommit=True
    )

async def setup_database():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS federal_documents (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    document_number VARCHAR(255) UNIQUE NOT NULL,
                    title TEXT,
                    publication_date DATE,
                    document_type VARCHAR(255),
                    abstract TEXT,
                    html_url VARCHAR(1024),
                    raw_data JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            print("Database table 'federal_documents' ensured to exist.")
    pool.close()
    await pool.wait_closed()

if __name__ == "__main__":
    asyncio.run(setup_database())   