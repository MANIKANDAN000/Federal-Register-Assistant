import asyncio
import aiomysql
import os
import json
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

async def get_db_pool_agent(): # Renamed to avoid conflict if imported elsewhere
    return await aiomysql.create_pool(
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        db=os.getenv("MYSQL_DB"),
        autocommit=True, # Simpler for read queries
        cursorclass=aiomysql.cursors.DictCursor # Get results as dictionaries
    )

# Tool definition for the LLM
# This schema will be sent to the LLM so it knows how to call the function.
search_federal_documents_tool_schema = {
    "type": "function",
    "function": {
        "name": "search_federal_documents_in_db",
        "description": "Searches the Federal Register documents database. Use this to find information about rules, proposed rules, notices, and presidential documents published in the Federal Register. Always try to use a specific date or date range if the user implies one, or if it's a recent query. Dates should be in YYYY-MM-DD format.",
        "parameters": {
            "type": "object",
            "properties": {
                "search_term": {
                    "type": "string",
                    "description": "A keyword or phrase to search for in the document title or abstract. Example: 'artificial intelligence regulations'"
                },
                "document_type": {
                    "type": "string",
                    "description": "Filter by document type. Examples: 'Rule', 'Proposed Rule', 'Notice', 'Presidential Document'.",
                    "enum": ["Rule", "Proposed Rule", "Notice", "Presidential Document"] 
                },
                "start_date": {
                    "type": "string",
                    "description": "The start date for the search range (YYYY-MM-DD). Example: '2024-01-01'. Use for 'since date X' or 'after date X' queries."
                },
                "end_date": {
                    "type": "string",
                    "description": "The end date for the search range (YYYY-MM-DD). Example: '2024-01-15'. Use for 'until date X' or 'before date X' queries. If user asks for documents 'on' a specific date, set start_date and end_date to the same value."
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of documents to return. Default is 5, max is 20.",
                    "default": 5,
                    "maximum": 20 
                }
            },
            "required": [] # Make search_term optional; LLM might just want to filter by date/type
        }
    }
}


async def search_federal_documents_in_db(
    search_term: Optional[str] = None, 
    document_type: Optional[str] = None, 
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None, 
    limit: int = 5
) -> str:
    """
    Actual Python function that queries the MySQL database.
    The LLM will "call" this function by providing arguments for these parameters.
    """
    pool = await get_db_pool_agent()
    results_str = "No documents found matching your criteria or an error occurred."
    
    # Validate limit
    limit = min(max(1, limit), 20) # Ensure limit is between 1 and 20

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            query_parts = ["SELECT document_number, title, publication_date, document_type, abstract, html_url FROM federal_documents"]
            conditions = []
            params = []

            if search_term:
                conditions.append("(title LIKE %s OR abstract LIKE %s)")
                params.extend([f"%{search_term}%", f"%{search_term}%"])
            
            if document_type:
                conditions.append("document_type = %s")
                params.append(document_type)

            if start_date:
                conditions.append("publication_date >= %s")
                params.append(start_date)
            
            if end_date:
                conditions.append("publication_date <= %s")
                params.append(end_date)

            if conditions:
                query_parts.append("WHERE " + " AND ".join(conditions))
            
            query_parts.append("ORDER BY publication_date DESC, id DESC") # Most recent first
            query_parts.append(f"LIMIT {limit}") # Use f-string for LIMIT as it's sanitized

            final_query = " ".join(query_parts)
            print(f"Executing SQL: {final_query} with params: {params}")

            try:
                await cur.execute(final_query, tuple(params))
                documents = await cur.fetchall()
                
                if documents:
                    # Format for LLM to summarize. Giving key info.
                    formatted_docs = []
                    for doc in documents:
                        # Truncate abstract for brevity if too long
                        abstract_summary = doc.get('abstract', '')
                        if abstract_summary and len(abstract_summary) > 200:
                            abstract_summary = abstract_summary[:200] + "..."
                        
                        formatted_docs.append({
                            "document_number": doc.get("document_number"),
                            "title": doc.get("title"),
                            "publication_date": str(doc.get("publication_date")), # Ensure string
                            "type": doc.get("document_type"),
                            "abstract_preview": abstract_summary,
                            "url": doc.get("html_url")
                        })
                    results_str = json.dumps(formatted_docs) # Return as JSON string for LLM
                else:
                    results_str = "No documents found matching your criteria."

            except Exception as e:
                print(f"Error querying database: {e}")
                results_str = f"Error querying database: {str(e)}"
    
    pool.close()
    await pool.wait_closed()
    print(f"Tool search_federal_documents_in_db result: {results_str[:500]}...") # Log snippet
    return results_str

# This dictionary maps tool names (as the LLM knows them) to actual Python functions
AVAILABLE_TOOLS = {
    "search_federal_documents_in_db": search_federal_documents_in_db
}

# And a list of schemas for the LLM
TOOL_DEFINITIONS = [
    search_federal_documents_tool_schema
]

if __name__ == '__main__':
    # Test the tool function
    async def test_tool():
        # result = await search_federal_documents_in_db(search_term="environmental protection", limit=2)
        # result = await search_federal_documents_in_db(document_type="Rule", start_date="2024-07-01", end_date="2024-07-15", limit=3)
        result = await search_federal_documents_in_db(search_term="executive order", document_type="Presidential Document", limit=2)
        print("\n--- Test Tool Result ---")
        print(result)

    # Make sure you have some data in the DB by running the pipeline first.
    # Example: python -m data_pipeline.run_pipeline
    # Then run this: python -m agent.tools
    # asyncio.run(test_tool())
    pass