# app.py

import os
import re
import csv
import uuid
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import openai
import bleach  # For enhanced input sanitization

# ===========================
# 1. Environment Setup
# ===========================

# Load environment variables from .env file
load_dotenv()

# Retrieve OpenAI API key from environment variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not OPENAI_API_KEY:
    raise ValueError("OpenAI API key not found. Please set it in the .env file.")

# ===========================
# 2. Flask App Initialization
# ===========================

app = Flask(__name__)
CORS(app)  # Enable CORS if frontend is on a different origin

# ===========================
# 3. Logging Configuration
# ===========================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ===========================
# 4. OpenAI Client Initialization
# ===========================

openai.api_key = OPENAI_API_KEY

def call_openai_api(prompt: str, max_tokens: int = 800) -> str:
    """
    Calls the OpenAI API with the given prompt and returns the response text.
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Your name is Clancy, and you are a College Research Assistant. "
                        "Your target audience is high school students who want to choose a major based on their career interests. "
                        "Connect their major selection to their college interests by providing detailed information about the college and the chosen major. "
                        "If there's no perfect match, suggest a close alternative."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"OpenAI API error: {str(e)}")
        return ""

# ===========================
# 5. CSV File Management
# ===========================

CSV_FILE = 'user_choices.csv'

def initialize_csv():
    """
    Initializes the CSV file with headers if it doesn't exist.
    """
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            # Updated headers to include 'current_state'
            writer.writerow(['session_id', 'name', 'timestamp', 'current_state', 'major_selected', 'college_researched'])
        logger.info(f"Created new CSV file: {CSV_FILE}")

initialize_csv()

def add_interaction(session_id, name=None, current_state=None, major_selected=None, college_researched=None):
    """
    Adds a new interaction to the CSV file.
    """
    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([
            session_id,
            name or '',
            datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            current_state or '',
            major_selected or '',
            college_researched or ''
        ])
    logger.info(f"Added interaction: session_id={session_id}, name={name}, current_state={current_state}, major_selected={major_selected}, college_researched={college_researched}")

def get_last_interaction(session_id):
    """
    Retrieves the last interaction for a given session_id.
    """
    with open(CSV_FILE, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        interactions = [row for row in reader if row['session_id'] == session_id]
        return interactions[-1] if interactions else None

def get_user_majors(session_id):
    """
    Retrieves all majors selected by the user in a given session.
    """
    with open(CSV_FILE, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        majors = [row['major_selected'] for row in reader if row['session_id'] == session_id and row['major_selected']]
        return majors

# ===========================
# 6. Input Sanitization
# ===========================

def sanitize_input(user_input):
    """
    Sanitizes user input by removing potentially harmful characters using bleach.
    """
    return bleach.clean(user_input, tags=[], strip=True)

# ===========================
# 7. Helper Functions
# ===========================

def parse_majors_list(majors_str: str) -> list:
    """
    Parses the majors list returned by OpenAI into a clean list of majors.
    """
    if not majors_str:
        return []

    majors = []
    lines = majors_str.split('\n')

    for line in lines:
        line = line.strip(' -*•\t')
        if not line:
            continue

        # Remove numbering if present
        line = re.sub(r'^\d+[\.\)]\s*', '', line)
        line = line.replace('*', '').replace('"', '').replace(':', '').strip()

        if line and len(line) > 2 and not line.lower().startswith(('here', 'the', 'this', 'certainly')):
            majors.append(line)

    return majors[:4]  # Ensure exactly 4 majors

def format_response(sections):
    """
    Takes a list of HTML-formatted sections and joins them with section breaks.
    """
    return "<section_break>".join(sections)

def extract_tags(text):
    """
    Extracts special tags from the text to control frontend UI elements.
    """
    return re.findall(r'\[(.*?)\]', text)

def get_major_sections(major: str) -> list:
    """
    Retrieves structured information about a major using OpenAI.
    """
    prompt = f"""Provide detailed information about the {major} major tailored for high school students. Use the following HTML format with bold headings and bullet points:

<h2>PROGRAM OVERVIEW</h2>
<ul>
<li><strong>Program Description:</strong> </li>
<li><strong>Key Features:</strong> </li>
<li><strong>Duration and Structure:</strong> </li>
</ul>

<h2>CORE SKILLS</h2>
<ul>
<li><strong>Technical Abilities:</strong> </li>
<li><strong>Professional Skills:</strong> </li>
<li><strong>Key Competencies:</strong> </li>
</ul>

<h2>COURSEWORK</h2>
<ul>
<li><strong>Foundation Courses:</strong> </li>
<li><strong>Advanced Topics:</strong> </li>
<li><strong>Specializations:</strong> </li>
</ul>

<h2>CAREER PATHS</h2>
<ul>
<li><strong>Entry-Level Positions:</strong> </li>
<li><strong>Career Progression:</strong> </li>
<li><strong>Industry Sectors:</strong> </li>
</ul>

Ensure clarity, conciseness, and relevance to high school students considering this major.
"""
    response = call_openai_api(prompt)
    if not response:
        return ["<h2>PROGRAM OVERVIEW</h2><ul><li><strong>Program Description:</strong> Unable to retrieve information at this time.</li></ul>"]

    # Split by <h2> to separate sections
    sections = [section.strip() for section in re.split(r'<h2>', response) if section.strip()]
    formatted_sections = [f"<h2>{section}" for section in sections]
    return formatted_sections

def get_college_info(college: str, user_majors: list) -> list:
    """
    Retrieves structured information about a college, including details relevant to the user's selected majors.
    """
    # Basic college information prompt
    basic_prompt = f"""Provide detailed information about {college} tailored for high school students. Use the following HTML format with bold headings and bullet points:

<h2>INSTITUTION OVERVIEW</h2>
<ul>
<li><strong>Type and Location:</strong> </li>
<li><strong>Size and Environment:</strong> </li>
<li><strong>Key Features:</strong> </li>
</ul>

<h2>ACADEMIC PROFILE</h2>
<ul>
<li><strong>Notable Programs:</strong> </li>
<li><strong>Research Opportunities:</strong> </li>
<li><strong>Academic Resources:</strong> </li>
</ul>

Ensure clarity, conciseness, and relevance to high school students considering this college.
"""
    sections = []
    basic_info = call_openai_api(basic_prompt)
    if basic_info:
        basic_sections = [sec.strip() for sec in re.split(r'<h2>', basic_info) if sec.strip()]
        formatted_basic_sections = [f"<h2>{section}" for section in basic_sections]
        sections.extend(formatted_basic_sections)
    else:
        sections.append("<h2>INSTITUTION OVERVIEW</h2><ul><li><strong>Type and Location:</strong> Unable to retrieve basic college info at this time.</li></ul>")

    # Major-specific sections if any majors selected
    if user_majors:
        for major in user_majors:
            major_prompt = f"""Provide detailed information about the {major} program at {college} tailored for high school students. Use the following HTML format with bold headings and bullet points:

<h2>{major.upper()} PROGRAM</h2>
<ul>
<li><strong>Program Availability:</strong> </li>
<li><strong>Department Details:</strong> </li>
<li><strong>Special Features:</strong> </li>
<li><strong>Career Support:</strong> </li>
</ul>

Ensure clarity, conciseness, and relevance to high school students considering this major at {college}.
"""
            major_info = call_openai_api(major_prompt)
            if major_info:
                major_sections = [sec.strip() for sec in re.split(r'<h2>', major_info) if sec.strip()]
                formatted_major_sections = [f"<h2>{section}" for section in major_sections]
                sections.extend(formatted_major_sections)
            else:
                sections.append(f"<h2>{major.upper()} PROGRAM</h2><ul><li><strong>Program Availability:</strong> Unable to retrieve major-specific information at this time.</li></ul>")
    else:
        # If no majors have been chosen yet
        sections.append("<h2>MAJOR-SPECIFIC INFORMATION</h2><ul><li>No majors have been selected yet, so no tailored information is available.</li></ul>")

    return sections

# ===========================
# 8. Route Definitions
# ===========================

@app.route('/')
def index():
    """
    Serves the main chat interface.
    """
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    """
    Handles chat messages from the frontend and responds accordingly.
    """
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        client_session_id = data.get('session_id')  # Expecting session_id from frontend

        logger.info(f"Received message: '{user_message}' with session_id: '{client_session_id}'")

        # Generate a new session_id if not provided
        if not client_session_id:
            session_id = str(uuid.uuid4())
            logger.info(f"Generated new session_id: {session_id}")
            # Initial state is 'ASK_NAME'
            add_interaction(session_id, current_state='ASK_NAME')
        else:
            session_id = client_session_id
            logger.info(f"Using existing session_id: {session_id}")

        # Prepare response data
        response_data = {"session_id": session_id}

        # Check for 'INIT' message
        if user_message.upper() == "INIT":
            response_text = (
                "Hello! I'm Clancy, your College Research Assistant. I'm here to help you explore colleges and majors.<br><br>"
                "Please type your name to begin:<br><strong>[ASK_NAME]</strong>"
            )
            response_data["response"] = response_text
            return jsonify(response_data)

        # Retrieve the last interaction
        last_interaction = get_last_interaction(session_id)

        # Determine the conversation flow based on the current state
        current_state = last_interaction['current_state'] if last_interaction else 'ASK_NAME'

        if current_state == 'ASK_NAME':
            # Assume the user is providing their name
            name = sanitize_input(user_message)
            add_interaction(session_id, name=name, current_state='MAIN_MENU')
            response_text = (
                f"Nice to meet you, {name}! How can I help you today?<br><br>"
                "<strong>Options:</strong><br>"
                "- Explore Careers and Majors<br>"
                "- Research Colleges<br>"
                "- Get Application Advice<br><strong>[MAIN_MENU]</strong>"
            )
            response_data["response"] = response_text
            return jsonify(response_data)

        elif current_state == 'MAIN_MENU':
            # Handle user selection from the main menu
            choice = user_message.lower()
            if choice == "explore careers and majors":
                add_interaction(session_id, current_state='ASK_CAREER')
                response_text = "What career field are you interested in?<br><strong>[ASK_CAREER]</strong>"
                response_data["response"] = response_text
                return jsonify(response_data)
            elif choice == "research colleges":
                add_interaction(session_id, current_state='ASK_COLLEGE')
                response_text = "Which college would you like to learn about?<br><strong>[ASK_COLLEGE]</strong>"
                response_data["response"] = response_text
                return jsonify(response_data)
            elif choice == "get application advice":
                # Provide preformatted advice sections with HTML
                sections = [
                    """<h2>APPLICATION PLANNING</h2>
<ul>
<li><strong>Start Early (Junior Year)</strong></li>
<li><strong>Research Schools</strong></li>
<li><strong>Create a Timeline</strong></li>
<li><strong>Gather Materials</strong></li>
</ul>""",
                    """<h2>KEY COMPONENTS</h2>
<ul>
<li><strong>Personal Essays</strong></li>
<li><strong>Recommendation Letters</strong></li>
<li><strong>Test Scores</strong></li>
<li><strong>Activities List</strong></li>
</ul>""",
                    """<h2>WRITING TIPS</h2>
<ul>
<li><strong>Be Authentic</strong></li>
<li><strong>Show, Don't Tell</strong></li>
<li><strong>Start Early</strong></li>
<li><strong>Get Feedback</strong></li>
</ul>""",
                    """<h2>FINAL STEPS</h2>
<ul>
<li><strong>Double Check Everything</strong></li>
<li><strong>Meet Deadlines</strong></li>
<li><strong>Keep Copies</strong></li>
<li><strong>Follow Up</strong></li>
</ul>"""
                ]
                formatted_response = format_response(sections) + "<br><strong>[MAIN_MENU]</strong>"
                add_interaction(session_id, current_state='MAIN_MENU')
                response_data["response"] = formatted_response
                return jsonify(response_data)
            else:
                # Unrecognized option, prompt again
                response_text = (
                    "Please select one of the options below:<br>"
                    "- Explore Careers and Majors<br>"
                    "- Research Colleges<br>"
                    "- Get Application Advice<br><strong>[MAIN_MENU]</strong>"
                )
                response_data["response"] = response_text
                return jsonify(response_data)

        elif current_state == 'ASK_CAREER':
            # User is providing a career field
            career_field = sanitize_input(user_message)
            prompt = (
                f"List exactly 4 college majors suitable for a career in {career_field}. "
                "List ONLY the major names, numbered 1-4. "
                "No descriptions or extra text."
            )
            majors_response = call_openai_api(prompt)
            if not majors_response:
                response_data["response"] = "I'm having trouble suggesting majors right now. Please try again.<br><strong>[ASK_CAREER]</strong>"
                return jsonify(response_data)

            majors = parse_majors_list(majors_response)
            if len(majors) != 4:
                response_data["response"] = "I'm having trouble processing the majors. Please try another career field.<br><strong>[ASK_CAREER]</strong>"
                return jsonify(response_data)

            # Store the majors in 'major_selected' field
            add_interaction(session_id, current_state='SHOW_MAJORS', major_selected=", ".join(majors))
            majors_html = "<br>".join([f"{i+1}. {m}" for i, m in enumerate(majors, 1)])
            response_text = (
                f"Here are some majors to consider:<br><br>{majors_html}<br><br>"
                "Select one to learn more by typing the number or the name:<br><strong>[SHOW_MAJORS]</strong>"
            )
            response_data["response"] = response_text
            return jsonify(response_data)

        elif current_state == 'SHOW_MAJORS':
            # User is selecting a major
            selected_major = sanitize_input(user_message)
            majors = last_interaction['major_selected'].split(", ")
            if user_message.isdigit():
                index = int(user_message) - 1
                if 0 <= index < len(majors):
                    selected_major = majors[index]
                else:
                    selected_major = None
            elif user_message in majors:
                selected_major = user_message
            else:
                selected_major = None

            if selected_major:
                add_interaction(session_id, current_state='MAIN_MENU', major_selected=selected_major)
                sections = get_major_sections(selected_major)
                formatted_response = format_response(sections) + "<br>What else would you like to know?<br><strong>[MAIN_MENU]</strong>"
                response_data["response"] = formatted_response
                return jsonify(response_data)
            else:
                majors_html = "<br>".join([f"{i+1}. {m}" for i, m in enumerate(majors, 1)])
                response_data["response"] = (
                    f"Please select a major from the list by typing the number or the name:<br><br>{majors_html}<br><strong>[SHOW_MAJORS]</strong>"
                )
                return jsonify(response_data)

        elif current_state == 'ASK_COLLEGE':
            # User is providing a college name
            college_name = sanitize_input(user_message)
            user_majors = get_user_majors(session_id)
            add_interaction(session_id, current_state='MAIN_MENU', college_researched=college_name)
            sections = get_college_info(college_name, user_majors)
            if not sections:
                response_data["response"] = "I'm having trouble getting information about this college. Please try another.<br><strong>[ASK_COLLEGE]</strong>"
                return jsonify(response_data)

            formatted_response = format_response(sections) + "<br>What else would you like to know?<br><strong>[MAIN_MENU]</strong>"
            response_data["response"] = formatted_response
            return jsonify(response_data)

        else:
            # Unhandled state, reset to MAIN_MENU
            response_text = (
                "I encountered an unexpected state. Let's start over.<br><br>"
                "<strong>Options:</strong><br>"
                "- Explore Careers and Majors<br>"
                "- Research Colleges<br>"
                "- Get Application Advice<br><strong>[MAIN_MENU]</strong>"
            )
            add_interaction(session_id, current_state='MAIN_MENU')
            response_data["response"] = response_text
            return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error in /chat endpoint: {str(e)}")
        # Ensure that session_id is defined before using it
        response_data = {
            "response": "I encountered an error. Please try again.<br><strong>[MAIN_MENU]</strong>",
            "session_id": session_id if 'session_id' in locals() else None
        }
        return jsonify(response_data), 500

# ===========================
# 9. Running the App
# ===========================

if __name__ == '__main__':
    app.run(debug=True, port=5000)
