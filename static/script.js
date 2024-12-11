const CONFIG = {
    API_URL: "http://localhost:5000",
    MAX_MESSAGE_LENGTH: 500,
    INIT_MESSAGE: "INIT",
    MESSAGE_DELAY: 800
};

// Initialize chat when page loads
document.addEventListener('DOMContentLoaded', async () => {
    console.log("Page loaded, initializing chat...");
    await sendMessage(CONFIG.INIT_MESSAGE, true);
});

// Event Listeners
document.getElementById('send-btn')?.addEventListener('click', () => sendMessage());

document.getElementById('user-input')?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        e.preventDefault();
        sendMessage();
    }
});

// Initialize button listeners
function initializeButtonListeners() {
    document.querySelectorAll('.choice-btn').forEach(button => {
        // Remove existing listeners to prevent duplicates
        button.replaceWith(button.cloneNode(true));
        const newButton = document.querySelector(`[data-choice="${button.getAttribute('data-choice')}"]`);
        newButton.addEventListener('click', buttonClickHandler);
    });
}

function buttonClickHandler(event) {
    const choice = event.target.getAttribute('data-choice') || event.target.textContent;
    console.log("Choice clicked:", choice);
    sendMessage(choice);
}

// Message handling
async function sendMessage(forcedMessage = null, isInit = false) {
    try {
        const userInput = document.getElementById('user-input');
        const message = forcedMessage || userInput?.value?.trim();

        if (!message) return;

        if (!isInit) {
            addUserMessage(message);
        }

        // Show typing indicator
        addTypingIndicator();

        if (!forcedMessage && userInput) {
            userInput.value = '';
        }

        const response = await callAPI(message);
        
        // Remove typing indicator
        removeTypingIndicator();

        if (response && response.response) {
            handleBotMessage(response.response);
        }
    } catch (error) {
        console.error("Message sending failed:", error);
        removeTypingIndicator();
        addErrorMessage("Sorry, I encountered an error. Please try again.");
    }
}

async function callAPI(message) {
    try {
        const response = await fetch(`${CONFIG.API_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                message: message,
                session_id: localStorage.getItem('session_id')
            })
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        const data = await response.json();
        if (data.session_id) {
            localStorage.setItem('session_id', data.session_id);
        }
        return data;
    } catch (error) {
        console.error("API call failed:", error);
        throw error;
    }
}

function handleBotMessage(text) {
    // Remove any existing typing indicator
    removeTypingIndicator();
    
    if (text.includes("<section_break>")) {
        const messages = text.split("<section_break>");
        messages.forEach((msg, index) => {
            setTimeout(() => {
                if (msg.trim()) {
                    addBotMessage(msg.trim());
                }
            }, index * CONFIG.MESSAGE_DELAY);
        });
    } else {
        addBotMessage(text);
    }
}

// Message UI functions
function addUserMessage(text) {
    const messageElement = document.createElement('div');
    messageElement.className = 'chat-message user';
    messageElement.textContent = text;
    appendMessage(messageElement);
}

function addBotMessage(text) {
    const messageElement = document.createElement('div');
    messageElement.className = 'chat-message bot';
    
    // Remove tags for display but keep them for processing
    const tags = extractTags(text);
    const cleanText = text.replace(/\[.*?\]/g, '').trim();
    messageElement.innerHTML = cleanText;
    
    const messagesDiv = document.getElementById('messages');
    if (messagesDiv) {
        messagesDiv.appendChild(messageElement);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    updateUIElements(tags);
}

function addErrorMessage(text) {
    const messageElement = document.createElement('div');
    messageElement.className = 'chat-message error';
    messageElement.textContent = text;
    appendMessage(messageElement);
}

function appendMessage(messageElement) {
    const messagesDiv = document.getElementById('messages');
    if (messagesDiv) {
        messagesDiv.appendChild(messageElement);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
}

// Typing indicator functions
function addTypingIndicator() {
    removeTypingIndicator(); // Remove any existing indicator
    const messagesDiv = document.getElementById('messages');
    if (messagesDiv) {
        const typingElement = document.createElement('div');
        typingElement.className = 'chat-message bot typing-indicator';
        typingElement.textContent = 'Clancy is typing...';
        messagesDiv.appendChild(typingElement);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
}

function removeTypingIndicator() {
    const typingMessage = document.querySelector('.typing-indicator');
    if (typingMessage) {
        typingMessage.remove();
    }
}

// UI helper functions
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
    const regex = /\d+\.\s*([^\n]+)/g;

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
        if (show) {
            initializeButtonListeners();
        }
    }
}

function showMajors(show, majors = []) {
    const majorsDiv = document.getElementById('majors-buttons');
    if (!majorsDiv) return;

    majorsDiv.innerHTML = ''; // Clear existing content
    majorsDiv.style.display = show ? 'block' : 'none';

    if (show && majors.length > 0) {
        const buttonGroup = document.createElement('div');
        buttonGroup.className = 'button-group many-options';

        majors.forEach((major, index) => {
            const button = document.createElement('button');
            button.className = 'choice-btn';
            button.setAttribute('data-major', major);
            button.textContent = `${index + 1}. ${major}`;
            button.onclick = () => sendMessage(major);
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
        if (show) {
            input.focus();
        }
    }
}