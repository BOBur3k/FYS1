// script.js

const CONFIG = {
    API_URL: "http://localhost:5000",
    MAX_MESSAGE_LENGTH: 500,
    INIT_MESSAGE: "INIT",
    MESSAGE_DELAY: 800
};

// Initialize sessionId from localStorage if it exists
let sessionId = localStorage.getItem('sessionId') || null;

document.addEventListener('DOMContentLoaded', async () => {
    console.log("Page loaded, initializing chat...");

    if (!sessionId) {
        // Send INIT only if there's no existing sessionId
        await sendMessage(CONFIG.INIT_MESSAGE, true);
    } else {
        // Optionally, you can send a welcome back message or fetch the current state
        addMessageToChat("Clancy: Welcome back! How can I assist you today?", false);
        showMainMenu(true);
    }
});

// Event Listeners
document.getElementById('send-btn')?.addEventListener('click', () => sendMessage());

document.getElementById('user-input')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        e.preventDefault();
        sendMessage();
    }
});

// Use event delegation for dynamically added buttons
document.getElementById('interaction-area')?.addEventListener('click', async (e) => {
    if (e.target && e.target.classList.contains('choice-btn')) {
        const choice = e.target.getAttribute('data-choice');
        if (choice) {
            console.log("Choice clicked:", choice);
            await sendMessage(choice);
        }
    }
});

async function sendMessage(forcedMessage = null, isInit = false) {
    try {
        const userInput = document.getElementById('user-input');
        const message = forcedMessage || userInput?.value?.trim();

        if (!message) return;

        if (!isInit) {
            addMessageToChat("You: " + message, true);
        }

        if (!forcedMessage && userInput) {
            userInput.value = '';
        }

        // Show loading indicator
        showLoading(true);

        const response = await callAPI(message);
        if (response && response.response) {
            handleBotMessage(response.response);
            // Update sessionId if provided
            if (response.session_id) {
                sessionId = response.session_id;
                localStorage.setItem('sessionId', sessionId); // Store sessionId in localStorage
                console.log("Session ID updated:", sessionId);
            }
        }

        // Hide loading indicator
        showLoading(false);
    } catch (error) {
        console.error("Message sending failed:", error);
        addMessageToChat("Bot: Sorry, I encountered an error. Please try again.", false);
        showLoading(false);
    }
}

async function callAPI(message) {
    try {
        const payload = {
            message: message
        };
        if (sessionId) {
            payload.session_id = sessionId;
        }

        const response = await fetch(`${CONFIG.API_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error("API call failed:", error);
        throw error;
    }
}

function handleBotMessage(text) {
    if (text.includes("<section_break>")) {
        const messages = text.split("<section_break>");
        messages.forEach((msg, index) => {
            setTimeout(() => {
                if (msg.trim()) {
                    addProcessedMessage(msg.trim());
                }
            }, index * CONFIG.MESSAGE_DELAY);
        });
    } else {
        addProcessedMessage(text);
    }
}

function addProcessedMessage(text) {
    const tags = extractTags(text);
    const cleanText = text.replace(/\[.*?\]/g, '').trim();

    if (cleanText) {
        addMessageToChat("Clancy: " + cleanText, false);
    }

    updateUIElements(tags);
}

function addMessageToChat(text, isUser = false) {
    const messagesDiv = document.getElementById('messages');
    if (messagesDiv) {
        const messageElement = document.createElement('div');
        messageElement.className = `chat-message ${isUser ? 'user' : 'bot'}`;
        
        // Remove the "Clancy: " or "You: " prefix
        const cleanText = text.replace(/^(Clancy: |You: )/, '');
        // Sanitize the HTML content
        messageElement.innerHTML = DOMPurify.sanitize(cleanText);
        
        messagesDiv.appendChild(messageElement);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
}

function extractTags(text) {
    const tags = [];
    const tagRegex = /\[(.*?)\]/g;
    let match;
    while ((match = tagRegex.exec(text)) !== null) {
        tags.push(match[0]);
    }
    return tags;
}

function updateUIElements(tags) {
    showMainMenu(false);
    showMajors(false);
    showInputField(false);

    tags.forEach(tag => {
        if (tag === "[SHOW_MAJORS]") {
            const majors = extractMajorsFromLastMessage();
            if (majors.length > 0) {
                showMajors(true, majors);
            }
        }
        if (tag === "[ASK_NAME]") showInputField(true, "Type your name here...");
        if (tag === "[MAIN_MENU]") showMainMenu(true);
        if (tag === "[ASK_CAREER]") showInputField(true, "Type the career here...");
        if (tag === "[ASK_COLLEGE]") showInputField(true, "Type the college name here...");
    });
}

function extractMajorsFromLastMessage() {
    const messagesDiv = document.getElementById('messages');
    const messages = messagesDiv.getElementsByClassName('chat-message');
    if (messages.length === 0) return [];

    const lastMessage = messages[messages.length - 1];
    const majors = [];
    const regex = /\d+\.\s*([^:\n]+)/g;
    let match;

    while ((match = regex.exec(lastMessage.textContent)) !== null) {
        majors.push(match[1].trim());
    }

    return majors;
}

function showMainMenu(show) {
    const menu = document.getElementById('main-menu-buttons');
    if (menu) {
        menu.style.display = show ? 'block' : 'none';
    }
}

function showMajors(show, majors = []) {
    const majorsDiv = document.getElementById('majors-buttons');
    if (!majorsDiv) return;

    majorsDiv.innerHTML = '';
    majorsDiv.style.display = show ? 'block' : 'none';

    if (show && majors.length > 0) {
        const buttonGroup = document.createElement('div');
        buttonGroup.className = 'button-group many-options';
        
        majors.forEach(major => {
            const button = document.createElement('button');
            button.className = 'choice-btn';
            button.setAttribute('data-choice', major);
            button.textContent = major;
            buttonGroup.appendChild(button);
        });
        
        majorsDiv.appendChild(buttonGroup);
    }
}

function showInputField(show, placeholder = '') {
    const container = document.getElementById('input-container');
    const input = document.getElementById('user-input');
    
    if (container && input) {
        input.value = '';
        input.placeholder = placeholder;
        container.style.display = show ? 'flex' : 'none';
    }
}

function showLoading(show) {
    const loadingDiv = document.getElementById('loading');
    if (loadingDiv) {
        loadingDiv.style.display = show ? 'block' : 'none';
    }
}
