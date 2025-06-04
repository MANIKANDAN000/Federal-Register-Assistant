document.addEventListener('DOMContentLoaded', () => {
    const chatBox = document.getElementById('chat-box');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    let sessionId = null;

    // Function to add a message to the chat box
    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender);
        // Basic sanitization to prevent HTML injection from text
        const textNode = document.createTextNode(text); 
        messageDiv.appendChild(textNode);
        chatBox.appendChild(messageDiv);
        chatBox.scrollTop = chatBox.scrollHeight; // Scroll to bottom
    }
    
    // Function to generate a new session ID
    async function getSessionId() {
        try {
            const response = await fetch('/generate-session', { method: 'POST' });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            sessionId = data.session_id;
            console.log("Session ID:", sessionId);
        } catch (error) {
            console.error("Error generating session ID:", error);
            addMessage("Error: Could not start a new session. Please refresh.", "error");
            sendButton.disabled = true;
        }
    }

    // Function to send message to backend
    async function sendMessage() {
        const messageText = userInput.value.trim();
        if (!messageText) return;
        if (!sessionId) {
            addMessage("Error: No active session. Please refresh.", "error");
            return;
        }

        addMessage(messageText, 'user');
        userInput.value = ''; // Clear input
        sendButton.disabled = true; // Disable button while waiting

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ session_id: sessionId, message: messageText }),
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: "Unknown server error" }));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            addMessage(data.response, 'assistant');

        } catch (error) {
            console.error('Error sending message:', error);
            addMessage(`Error: ${error.message || "Could not get response from server."}`, 'error');
        } finally {
            sendButton.disabled = false; // Re-enable button
            userInput.focus();
        }
    }

    // Event listeners
    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            sendMessage();
        }
    });

    // Initialize session
    getSessionId();
});