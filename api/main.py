from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uuid
import os

from agent.llm_agent import get_agent_response # The core agent logic

# Create app
app = FastAPI(title="Federal RAG Agent API")

# Mount static files (for HTML, CSS, JS)
# Ensure the 'static' directory is at api/static
current_dir = os.path.dirname(os.path.abspath(__file__))
static_dir = os.path.join(current_dir, "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Templates for serving HTML
templates_dir = static_dir # HTML is in static too
templates = Jinja2Templates(directory=templates_dir)

class ChatMessage(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    session_id: str
    response: str

@app.get("/")
async def get_chat_ui(request: Request):
    """Serves the main chat HTML page."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/chat", response_model=ChatResponse)
async def chat_with_agent(chat_message: ChatMessage):
    """
    Endpoint to send a message to the agent and get a response.
    A session_id is used to maintain conversation context.
    """
    print(f"Received message for session {chat_message.session_id}: {chat_message.message}")
    if not chat_message.message or not chat_message.session_id:
        raise HTTPException(status_code=400, detail="Session ID and message are required.")

    try:
        agent_reply = await get_agent_response(chat_message.session_id, chat_message.message)
        return ChatResponse(session_id=chat_message.session_id, response=agent_reply)
    except Exception as e:
        print(f"Error in /chat endpoint: {e}")
        # In a real app, log this exception properly
        # traceback.print_exc()
        raise HTTPException(status_code=500, detail="An internal error occurred.")

@app.post("/generate-session")
async def generate_session():
    """Generates a new unique session ID for the chat."""
    return {"session_id": str(uuid.uuid4())}


if __name__ == "__main__":
    import uvicorn
    # To run: uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
    # Make sure your current working directory is the root of `federal_rag_agent`
    # Or adjust Python path if needed.
    # Example: PYTHONPATH=. uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
    print("Starting Uvicorn server for FastAPI app...")
    print("Access the UI at http://localhost:8000/")
    print("Make sure Ollama is running and the model is pulled (e.g., qwen2:0.5b).")
    print("Make sure MySQL is running and data pipeline has been run at least once.")
    
    # This uvicorn.run() is for direct execution.
    # For production, use Gunicorn with Uvicorn workers.
    # uvicorn.run(app, host="0.0.0.0", port=8000) 
    # The command line `uvicorn api.main:app --reload` is generally better for development.