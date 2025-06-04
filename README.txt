# Federal RAG Agent System

This project implements a User Facing chat-style RAG (Retrieval Augmented Generation) Agentic System. The user asks queries, and an LLM (powered by local Ollama) provides answers using tools to query a MySQL database. The data in MySQL is updated daily via a data pipeline that fetches information from the Federal Registry API.

## Features

*   **Daily Data Pipeline:** Fetches recent documents from the Federal Registry API and stores them in MySQL.
    *   Downloader and Processor are separate.
    *   Keeps raw data records for a configurable number of days.
*   **Agentic LLM:** Uses a local LLM (e.g., `qwen2:0.5b`) via Ollama with function/tool calling capabilities.
    *   The agent can use a tool to query the MySQL database for Federal Register documents.
    *   Tool calls are not visible to the end-user in the final response.
*   **API Interface:** FastAPI application provides a chat endpoint.
*   **Basic UI:** Simple HTML, CSS, and JavaScript chat interface.
*   **Asynchronous Operations:** Utilizes `asyncio`, `aiohttp`, and `aiomysql` for non-blocking operations where feasible.
*   **Raw SQL:** Interacts with MySQL using raw SQL queries.

## Concepts Implemented

1.  Asynchronous Programming in Python
2.  MySQL Database Setup & Raw SQL Querying
3.  Basic APIs in Python (FastAPI)
4.  Agentic LLM Inference with Tool/Function Calling
5.  Basic Data Processing Pipeline

## Project Structure