const API_URL = "https://your-api-id.execute-api.your-region.amazonaws.com/prod"; // Replace with your API Gateway endpoint
const API_KEY = "YOUR_API_KEY_HERE"; // Replace with your actual API key from API Gateway

document.addEventListener('DOMContentLoaded', async () => {
    const initRes = await fetch('/init');
    // NOTE: This won't work on GitHub Pages because '/init' doesn't exist locally.
    // Instead, call the Lambda endpoint directly on page load or handle init differently.
    // For now, we assume you run a local server for init. If hosting fully on GitHub Pages,
    // you might remove /init and just do a first call to Lambda in script.js.
    // For demonstration, let's call Lambda directly:

    // Let's simulate init by calling Lambda with a special message "INIT"
    const data = await callAPI("INIT");
    handleBotMessage(data.response);
});

document.getElementById('send-btn').addEventListener('click', async () => {
    await sendMessage();
});

document.getElementById('user-input').addEventListener('keydown', async (e) => {
    if (e.key === 'Enter') {
        await sendMessage();
    }
});

document.querySelectorAll('.choice-btn').forEach(button => {
    button.addEventListener('click', async () => {
        const choice = button.getAttribute('data-choice');
        await sendMessage(choice);
    });
});

async function callAPI(message) {
    const response = await fetch(`${API_URL}/chat`, {
        method:'POST',
        headers:{
            'Content-Type':'application/json',
            'x-api-key': API_KEY
        },
        body: JSON.stringify({message})
    });
    return await response.json();
}

async function sendMessage(forcedMessage=null) {
    const userInput = document.getElementById('user-input');
    const message = forcedMessage ? forcedMessage : userInput.value.trim();
    if (message) {
        addMessageToChat("You: " + message);
        if (!forcedMessage) userInput.value = '';
        const data = await callAPI(message);
        handleBotMessage(data.response);
    }
}

function handleBotMessage(botMessage) {
    const lines = botMessage.split('\n');
    const tags = [];
    let displayMsg = [];
    for (let line of lines) {
        if (line.startsWith('[') && line.endsWith(']')) {
            tags.push(line);
        } else {
            displayMsg.push(line);
        }
    }

    const finalMessage = displayMsg.join('\n').trim();
    addMessageToChat("Bot: " + finalMessage);

    // Hide all components first
    showMainMenu(false);
    showMajors(false);
    showInputField(false);

    if (tags.includes("[ASK_NAME]")) {
        showInputField(true, "Type your name here...");
    }
    if (tags.includes("[MAIN_MENU]")) {
        showMainMenu(true);
    }
    if (tags.includes("[ASK_CAREER]")) {
        showInputField(true, "Type the career here...");
    }
    if (tags.includes("[ASK_COLLEGE]")) {
        showInputField(true, "Type the college name here...");
    }
    if (tags.includes("[SHOW_MAJORS]")) {
        // Extract majors
        const majors = [];
        for (let line of displayMsg) {
            line=line.trim();
            if (/^\d+\./.test(line)) {
                let parts=line.split('.',2);
                let majorName=parts[1].trim();
                majors.push(majorName);
            }
        }
        if (majors.length>0) {
            showMajors(true, majors);
            showInputField(false);
        }
    }
}

function showMainMenu(show) {
    document.getElementById('main-menu-buttons').style.display = show?'block':'none';
}

function showMajors(show, majors=[]) {
    const majorsDiv = document.getElementById('majors-buttons');
    majorsDiv.innerHTML='';
    majorsDiv.style.display=show?'block':'none';
    if (show) {
        for (let m of majors) {
            const btn = document.createElement('button');
            btn.className='choice-btn';
            btn.textContent=m;
            btn.addEventListener('click', async ()=> {
                await sendMessage(m);
            });
            majorsDiv.appendChild(btn);
        }
    }
}

function showInputField(show, placeholder='') {
    const input = document.getElementById('user-input');
    input.value='';
    input.placeholder=placeholder;
    document.getElementById('input-container').style.display= show?'flex':'none';
}

function addMessageToChat(text) {
    const messagesDiv = document.getElementById('messages');
    const p = document.createElement('p');
    p.textContent=text;
    messagesDiv.appendChild(p);
    messagesDiv.scrollTop=messagesDiv.scrollHeight;
}

