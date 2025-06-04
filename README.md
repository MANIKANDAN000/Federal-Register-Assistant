# Federal RAG Agent: Chat with Your Federal Register Data

This project implements a User-Facing Chat-Style Retrieval Augmented Generation (RAG) Agentic System. Users can ask queries about US Federal Register documents, and a local LLM (powered by Ollama) provides answers by utilizing tools to query a MySQL database. The system includes a daily data pipeline to keep the Federal Register information in the database up-to-date.

## Core Features

*   **Daily Data Pipeline:**
    *   Fetches recent documents daily from the official Federal Registry API.
    *   Processes and stores structured data (title, publication date, abstract, type, URL, etc.) into a local MySQL database.
    *   Maintains a history of raw downloaded data.
*   **Agentic LLM System:**
    *   Utilizes a local Large Language Model (e.g., `qwen2:0.5b`) run via Ollama.
    *   The LLM is equipped with a custom "tool" (function call) that allows it to query the MySQL database for relevant Federal Register documents based on the user's query.
    *   The agent interprets the user's query, decides if the tool is needed, formulates the database query parameters, receives the data, and then summarizes it or answers the question.
    *   Tool calls are internal to the agent and not directly visible in the final response to the user.
*   **API Interface:**
    *   A FastAPI backend provides a `/chat` endpoint to communicate with the agent.
    *   Manages a simple in-memory session-based chat history for conversational context.
*   **User Interface:**
    *   A basic web-based chat interface built with HTML, CSS, and JavaScript allows users to interact with the agent.
*   **Technology Stack:**
    *   **Python:** Core programming language.
    *   **FastAPI:** For building the asynchronous API.
    *   **Ollama:** For running local LLMs.
    *   **MySQL/MariaDB:** For storing structured Federal Register data.
    *   **`aiomysql`:** Asynchronous Python driver for MySQL.
    *   **`aiohttp`:** Asynchronous HTTP client for the data pipeline.
    *   **`openai` Python client:** Used to interact with the Ollama API (which mimics the OpenAI API structure).
    *   **HTML, CSS, JavaScript:** For the frontend UI.
    *   **`python-dotenv`:** For managing environment variables.

## Project Architecture Overview

1.  **Data Pipeline (Scheduled/Manual Daily Run):**
    *   `downloader.py`: Fetches new document data from `federalregister.gov`.
    *   `processor.py`: Cleans, transforms, and loads this data into the MySQL `federal_documents` table.
2.  **User Interaction Flow:**
    *   User types a query into the web UI (`index.html`).
    *   JavaScript (`script.js`) sends the query to the FastAPI `/chat` endpoint.
    *   FastAPI (`api/main.py`) receives the query and passes it to the `llm_agent.py`.
    *   The `llm_agent.py` (with the help of `tools.py`):
        *   Sends the query and conversation history to the Ollama LLM.
        *   The LLM may decide to use the `search_federal_documents_in_db` tool. If so, it returns a "tool call" request.
        *   The agent executes the tool (which queries MySQL via `aiomysql`).
        *   The tool's results (data from the database) are sent back to the LLM.
        *   The LLM uses these results to generate a final natural language response.
    *   The FastAPI endpoint returns this response to the UI.
    *   The UI displays the agent's response.

## How to Work with This Project

### 1. Setup and Installation

**(Follow these steps carefully if you haven't already)**

1.  **Prerequisites:**
    *   Python 3.8+
    *   Git
    *   XAMPP (with MariaDB/MySQL started) or a standalone MySQL/MariaDB server.
    *   Ollama installed and running (`ollama serve`).
        *   Pull a model: `ollama pull qwen2:0.5b` (or your chosen model).

2.  **Clone the Repository (if you haven't):**
    ```bash
    git clone <your-repository-url>
    cd federal_rag_agent
    ```

3.  **Create and Activate Python Virtual Environment:**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

4.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Configure Environment Variables:**
    *   Copy `.env_example` to `.env` (if an example is provided, otherwise create `.env` manually).
    *   Edit the `.env` file with your specific settings:
        ```env
        MYSQL_HOST=localhost
        MYSQL_PORT=3306
        MYSQL_USER=root # Your XAMPP/MySQL username
        MYSQL_PASSWORD=  # Your XAMPP/MySQL password (blank for default XAMPP root)
        MYSQL_DB=federal_registry_db

        OLLAMA_BASE_URL=http://localhost:11434/v1
        OLLAMA_MODEL=qwen2:0.5b # Must match a model you've pulled with Ollama
        RAW_DATA_RETENTION_DAYS=7
        ```

6.  **Set Up the Database:**
    *   Ensure your MySQL server (e.g., via XAMPP) is running.
    *   Using a MySQL client (like phpMyAdmin for XAMPP, or `mysql` command line):
        *   Create the database: `CREATE DATABASE federal_registry_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`
    *   Run the table setup script (from your project root in the terminal, with `venv` active):
        ```bash
        python -m data_pipeline.db_setup
        ```

### 2. Running the Data Pipeline

This step populates your database with Federal Register data. Run this initially and then ideally daily.

*   From your project root in the terminal (with `venv` active):
    ```bash
    python -m data_pipeline.run_pipeline
    ```
    This will fetch data for "yesterday" by default.

### 3. Running the Application

1.  **Ensure Ollama is running** (`ollama serve` in a separate terminal).
2.  **Start the FastAPI Backend Server:**
    *   From your project root in the terminal (with `venv` active):
        *   **Windows (CMD):**
            ```cmd
            set PYTHONPATH=.
            uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
            ```
        *   **Windows (PowerShell):**
            ```powershell
            $env:PYTHONPATH = "."
            uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
            ```
        *   **macOS/Linux (or if you modified `api/main.py` as suggested):**
            ```bash
            uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
            ```
    *(If you modified `api/main.py` to include `sys.path.insert(0, PROJECT_ROOT)`, you don't need the `PYTHONPATH` or `set PYTHONPATH` parts for any OS).*

3.  **Access the Chat UI:**
    *   Open your web browser and navigate to `http://localhost:8000`.
    *   Start asking questions related to Federal Register documents!

### 4. Development and Modification

*   **Backend Logic:**
    *   Agent behavior: `agent/llm_agent.py`
    *   Database tools: `agent/tools.py`
    *   API endpoints: `api/main.py`
*   **Data Pipeline:**
    *   Downloading: `data_pipeline/downloader.py`
    *   Processing & DB insertion: `data_pipeline/processor.py`
*   **Frontend UI:**
    *   Structure: `api/static/index.html`
    *   Behavior: `api/static/script.js`
    *   Styling: `api/static/style.css`

*   **Debugging:**
    *   Check the terminal running `uvicorn` for backend logs, Python errors, and tool call information.
    *   Use your browser's Developer Tools (F12 or Right-click > Inspect) to debug frontend JavaScript (Console, Network tabs) and inspect HTML/CSS.

### 5. Stopping the Application

*   Press `Ctrl+C` in the terminal window where `uvicorn` is running.
*   Press `Ctrl+C` in the terminal window where `ollama serve` is running (if you want to stop Ollama).
*   Stop MySQL via XAMPP Control Panel if you're done.

## Project Structure

federal_rag_agent/
├── data_pipeline/ # Scripts for fetching, processing, and storing data
│ ├── init.py
│ ├── db_setup.py # Creates DB table
│ ├── downloader.py # Downloads data from API
│ └── processor.py # Processes and inserts data into DB
│ └── run_pipeline.py # Orchestrates the pipeline
├── agent/ # Agent logic and tool definitions
│ ├── init.py
│ ├── llm_agent.py # Core agent logic, LLM interaction, tool dispatch
│ └── tools.py # Defines DB query tool and its schema
├── api/ # FastAPI application and UI
│ ├── init.py
│ ├── main.py # FastAPI app, API endpoints
│ └── static/ # Frontend files
│ ├── index.html
│ ├── script.js
│ └── style.css
├── data/ # Stores raw downloaded data (gitignored by default)
│ ├── raw/
│ └── processed/ # Can be used to mark processed files
├── .env # Environment variables (MySQL credentials, Ollama settings) - DO NOT COMMIT ACTUAL SECRETS
├── .env_example # Example structure for .env
├── requirements.txt # Python dependencies
├── .gitignore # Specifies intentionally untracked files by Git
└── README.md # This file


## Future Enhancements (Potential)

*   Persistent chat history (e.g., using SQLite or a dedicated DB table).
*   More sophisticated tools for the agent.
*   Integration with a Vector Database for semantic search over document content.
*   User authentication.
*   Improved UI/UX.
*   Automated scheduling for the data pipeline (e.g., cron job, Windows Task Scheduler).

---

Key things to add to your Git repository:
All the code files: *.py, *.html, *.css, *.js.
requirements.txt: So others can install the correct dependencies.
README.md: This file, to explain your project.
.env_example: An example file showing the structure of the .env file, but WITHOUT your actual passwords or sensitive information.
.gitignore: This is very important. It tells Git which files and folders to ignore. Create a file named .gitignore in your project root with at least the following:

# Python
__pycache__/
*.py[cod]
*$py.class
*.egg-info/
*.egg
venv/
.venv/
env/
.env # IMPORTANT: Do not commit your actual .env file with secrets

# Data files (if large or regenerated)
data/raw/
data/processed/
# *.json in data/ if you don't want to track any downloaded/processed files

# IDE / Editor specific
.vscode/
.idea/
*.suo
*.ntvs*
*.njsproj
*.sln
*.sw?


#How to Run 

Install Xampp (start Mysql , Apache)
Install ollama and start server 

1. python -m venv venv
2. venv\Scripts\activate
3. pip install -r requirements.txt
4. python -m data_pipeline.db_setup
5. python -m data_pipeline.run_pipeline
6. pip install aiofiles
7. python -m data_pipeline.run_pipeline
8. pip install streamlit
9. set PYTHONPATH=.
10. uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

Finally copy paste the url on chrome  :   http://localhost:8000
