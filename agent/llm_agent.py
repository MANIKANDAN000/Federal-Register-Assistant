import os
import json
import asyncio
from openai import AsyncOpenAI # Official OpenAI client, works with Ollama
from dotenv import load_dotenv
from agent.tools import AVAILABLE_TOOLS, TOOL_DEFINITIONS # Import from our tools module

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")

if not OLLAMA_BASE_URL or not OLLAMA_MODEL:
    raise ValueError("OLLAMA_BASE_URL and OLLAMA_MODEL must be set in .env")

# Initialize the AsyncOpenAI client for Ollama
# Note: Ollama might not use an API key, but the client might expect something.
# For Ollama, the key is often a placeholder like "ollama" or can be omitted
# if the client handles it gracefully. Let's try omitting it first.
# If issues, try api_key="ollama".
client = AsyncOpenAI(
    base_url=OLLAMA_BASE_URL,
    api_key='ollama' # Required by the openai package, even if Ollama doesn't use it
)

# In-memory store for chat histories (for demo purposes)
# In a real app, this would be a database.
chat_histories = {} # { "session_id": [{"role": "user", "content": "..."}, ...], ... }
MAX_HISTORY_LEN = 10 # Keep last 10 messages (user + assistant + tool)

async def get_agent_response(session_id: str, user_query: str) -> str:
    if session_id not in chat_histories:
        chat_histories[session_id] = [{
            "role": "system", 
            "content": (
                "You are a helpful assistant that can query a database of US Federal Register documents. "
                "When asked about documents, use the 'search_federal_documents_in_db' tool. "
                "Provide concise summaries based on the tool's output. "
                "Always inform the user if no documents are found or if there's an issue. "
                "If asked for current date, you can state you don't have direct access but can search recent documents."
                "Be polite and helpful."
            )
        }]

    current_history = chat_histories[session_id]
    current_history.append({"role": "user", "content": user_query})

    # Trim history if it's too long
    if len(current_history) > MAX_HISTORY_LEN:
        # Keep system prompt + last MAX_HISTORY_LEN-1 messages
        current_history = [current_history[0]] + current_history[-(MAX_HISTORY_LEN-1):]
        chat_histories[session_id] = current_history
    
    print(f"\n--- Current conversation history for session {session_id} (for LLM) ---")
    for msg in current_history:
        print(f"- {msg['role']}: {str(msg['content'])[:200]}...") # Log snippet
    print("--- End of history ---")


    try:
        print(f"Sending to LLM with model: {OLLAMA_MODEL}")
        response = await client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=current_history,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto" # Let the model decide if it needs a tool
        )
        
        response_message = response.choices[0].message
        # print(f"LLM raw response_message object: {response_message}")

        tool_calls = response_message.tool_calls

        if tool_calls:
            print(f"LLM requested tool call(s): {tool_calls}")
            # Append the assistant's message with tool calls to history
            current_history.append(response_message) # Model's turn, includes tool_calls

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args_str = tool_call.function.arguments
                
                if function_name not in AVAILABLE_TOOLS:
                    error_msg = f"Error: LLM tried to call unknown function '{function_name}'"
                    print(error_msg)
                    current_history.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": error_msg,
                    })
                    # Potentially let LLM try to recover or just return error to user
                    # For now, let's make another call to LLM with this error info
                    # This might not be strictly necessary if we are sure LLM won't hallucinate tools.

                else:
                    function_to_call = AVAILABLE_TOOLS[function_name]
                    try:
                        function_args = json.loads(function_args_str)
                        print(f"Calling tool: {function_name} with args: {function_args}")
                        
                        # Ensure args are passed correctly, especially if some are optional
                        # The tool function itself should handle Optional[str]=None etc.
                        function_response = await function_to_call(**function_args)
                        
                        print(f"Tool {function_name} response (snippet): {str(function_response)[:200]}...")
                        current_history.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": function_response, # Must be a string
                        })
                    except json.JSONDecodeError:
                        err_msg = f"Error: Invalid JSON arguments from LLM for {function_name}: {function_args_str}"
                        print(err_msg)
                        current_history.append({
                            "tool_call_id": tool_call.id, "role": "tool", "name": function_name, "content": err_msg
                        })
                    except Exception as e:
                        err_msg = f"Error executing tool {function_name}: {e}"
                        print(err_msg)
                        current_history.append({
                            "tool_call_id": tool_call.id, "role": "tool", "name": function_name, "content": err_msg
                        })

            # Now, send the history (including tool responses) back to the LLM for a final answer
            print("Sending conversation with tool results back to LLM for final response...")
            
            # Trim history again before the final call if it grew too much
            if len(current_history) > MAX_HISTORY_LEN:
                current_history = [current_history[0]] + current_history[-(MAX_HISTORY_LEN-1):]
                chat_histories[session_id] = current_history

            second_response = await client.chat.completions.create(
                model=OLLAMA_MODEL,
                messages=current_history
            )
            final_answer = second_response.choices[0].message.content
            current_history.append({"role": "assistant", "content": final_answer})
            print(f"LLM final response: {final_answer}")
            return final_answer
        
        else:
            # No tool call, LLM gave a direct answer
            final_answer = response_message.content
            current_history.append({"role": "assistant", "content": final_answer})
            print(f"LLM direct response: {final_answer}")
            return final_answer

    except Exception as e:
        print(f"Error in LLM communication or processing: {e}")
        # Log the error details, traceback etc. in a real app
        # traceback.print_exc() 
        error_message_for_user = "Sorry, I encountered an error while processing your request. Please try again."
        # Add this error to history so it doesn't loop on error
        current_history.append({"role": "assistant", "content": error_message_for_user})
        return error_message_for_user
    finally:
        # Ensure history is saved back, trimmed if needed
        if len(chat_histories[session_id]) > MAX_HISTORY_LEN:
           chat_histories[session_id] = [chat_histories[session_id][0]] + chat_histories[session_id][-(MAX_HISTORY_LEN-1):]


if __name__ == '__main__':
    # Test the agent
    async def run_test_conversation():
        session_id = "test_session_001"
        queries = [
            "Hello, what can you do?",
            "Are there any new executive orders related to technology published recently?",
            # "Summarize presidential documents about 'national security' from July 2024 for me."
            # "Find rules about environmental protection published after July 1st, 2024"
            # "What documents were published on July 10th, 2024?" # Needs data for this date
        ]
        for q in queries:
            print(f"\n\nUSER: {q}")
            response = await get_agent_response(session_id, q)
            print(f"AGENT: {response}")
            await asyncio.sleep(1) # Small delay

    # Make sure Ollama is running with qwen2:0.5b (or your chosen model)
    # e.g., `ollama serve` and then `ollama pull qwen2:0.5b`
    # And that you have data in MySQL from the pipeline
    # asyncio.run(run_test_conversation())
    pass