# Standard library imports
import os
import json
import uuid
import logging
import re
from datetime import datetime

# Third-party imports
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError
import bleach

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize OpenAI client
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ValueError("OpenAI API key not found. Please set it in the .env file.")

client = OpenAI(api_key=OPENAI_API_KEY)

# Constants
JSON_FILE = 'user_choices.json'

def initialize_json():
    """Initialize the JSON file with an empty structure if it doesn't exist."""
    if not os.path.exists(JSON_FILE):
        with open(JSON_FILE, mode='w', encoding='utf-8') as file:
            json.dump({"interactions": []}, file, indent=4)
        logger.info(f"Created new JSON file: {JSON_FILE}")

initialize_json()

def load_data():
    """Load data from the JSON file."""
    try:
        with open(JSON_FILE, mode='r', encoding='utf-8') as file:
            data = json.load(file)
        return data
    except Exception as e:
        logger.error(f"Error loading JSON data: {e}")
        return {"interactions": []}

def save_data(data):
    """Save data to the JSON file."""
    try:
        with open(JSON_FILE, mode='w', encoding='utf-8') as file:
            json.dump(data, file, indent=4)
        logger.info("Data successfully saved to JSON.")
    except Exception as e:
        logger.error(f"Error saving JSON data: {e}")

def add_interaction(session_id, name=None, current_state=None, major_selected=None, college_researched=None):
    """Add a new interaction to the JSON file."""
    try:
        data = load_data()
        last_interaction = get_last_interaction(session_id)
        preserved_name = name if name else (last_interaction.get('name') if last_interaction else '')

        new_interaction = {
            "session_id": session_id,
            "name": preserved_name,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "current_state": current_state or '',
            "major_selected": major_selected or '',
            "college_researched": college_researched or ''
        }

        data["interactions"].append(new_interaction)
        save_data(data)
        logger.info(f"Added interaction: session_id={session_id}, name={preserved_name}, state={current_state}")
    except Exception as e:
        logger.error(f"Failed to add interaction: {e}")

def get_last_interaction(session_id):
    """Get the last interaction for a given session_id."""
    data = load_data()
    interactions = [inter for inter in data["interactions"] if inter["session_id"] == session_id]
    return interactions[-1] if interactions else None

def get_user_majors(session_id):
    """Get all majors selected by the user in a given session."""
    data = load_data()
    majors = [
        inter['major_selected'] 
        for inter in data["interactions"] 
        if inter['session_id'] == session_id and inter['major_selected']
    ]
    return list(filter(None, majors))

def sanitize_input(user_input):
    """Sanitize user input."""
    return bleach.clean(user_input, tags=[], strip=True)

def call_openai_api(prompt: str, max_tokens: int = 800) -> str:
    """Call OpenAI API with error handling."""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Clancy, a College Research Assistant. "
                        "When providing information about colleges, stick to factual information. "
                        "If you're not confident about specific details, provide general information "
                        "about the type of institution and suggest what prospective students "
                        "should look for or ask about. Always maintain a helpful and informative tone."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7
        )
        content = response.choices[0].message.content.strip()
        return content
    except Exception as e:
        logger.error(f"OpenAI API error: {str(e)}")
        return None

def parse_majors_list(majors_str: str) -> list:
    """Parse majors from various formats into a list."""
    if not majors_str:
        return []
        
    # Split by commas and clean each major
    majors = [
        m.strip(' -•*\t.[]"')
        for m in majors_str.split(',')
        if m.strip(' -•*\t.[]"')
    ]
    
    # Remove any numbers at start
    majors = [re.sub(r'^\d+[\.\)]\s*', '', m) for m in majors]
    
    # Filter out empty or invalid entries
    majors = [m for m in majors if len(m) > 2]
    
    return majors[:4]

def call_openai_api_with_retries(prompt: str, retries: int = 800) -> str:
    """Call OpenAI API with retries for consistent format."""
    base_prompt = (
        f"You must respond with exactly 4 majors related to {prompt}, "
        "in a simple comma-separated list format. "
        "Example format: Political Science, International Relations, Public Policy, Economics"
    )
    
    for attempt in range(retries + 1):
        response = call_openai_api(base_prompt)
        logger.info(f"OpenAI response: {response}")  # Add logging
        
        if not response:
            continue
            
        majors = parse_majors_list(response)
        if len(majors) == 4:
            return ", ".join(majors)  # Return formatted list
            
        logger.warning(f"Attempt {attempt + 1}: Got {len(majors)} majors, retrying...")
        base_prompt = (
            "Provide exactly 4 majors separated by commas ONLY. "
            "Example: Major1, Major2, Major3, Major4"
        )
    
    return ""

def validate_career_input(career_input):
    """Basic career input validation."""
    return career_input.strip()

def format_response(sections):
    """Format sections with breaks."""
    return "<section_break>".join(sections)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_message = sanitize_input(data.get('message', '').strip())
        client_session_id = data.get('session_id')

        logger.info(f"Received message: '{user_message}' with session_id: '{client_session_id}'")

        # Handle INIT message
        if user_message.upper() == "INIT":
            session_id = str(uuid.uuid4())
            add_interaction(session_id, current_state='ASK_NAME')
            return jsonify({
                "session_id": session_id,
                "response": "Hello! I'm Clancy, your College Research Assistant. I'm here to help you explore colleges and majors.<br><br>Please type your name to begin:<br><strong>[ASK_NAME]</strong>"
            })

        # Use existing session_id or generate new one
        session_id = client_session_id or str(uuid.uuid4())
        last_interaction = get_last_interaction(session_id)
        current_state = last_interaction['current_state'] if last_interaction else 'ASK_NAME'

        response_data = {"session_id": session_id}

        # Handle states
        if current_state == 'ASK_NAME':
            name = user_message
            add_interaction(session_id, name=name, current_state='MAIN_MENU')
            response_text = (
                f"Nice to meet you, {name}!<br><br>"
                "How can I help you today?<br><br>"
                "<strong>Options:</strong><br>"
                "• Explore Careers and Majors<br>"
                "• Research Colleges<br>"
                "• Get Application Advice<br>"
                "<strong>[MAIN_MENU]</strong>"
            )
            response_data["response"] = response_text
            return jsonify(response_data)

        elif current_state == 'MAIN_MENU':
            choice = user_message.lower()
            
            if choice == "explore careers and majors":
                add_interaction(session_id, current_state='ASK_CAREER')
                response_text = "What career field are you interested in?<br><strong>[ASK_CAREER]</strong>"
                
            elif choice == "research colleges":
                add_interaction(session_id, current_state='ASK_COLLEGE')
                response_text = "Which college would you like to learn about?<br><strong>[ASK_COLLEGE]</strong>"
                
            elif choice == "get application advice":
                sections = [
                    """<h2>APPLICATION PLANNING</h2>
• Start Early (Junior Year)
• Research Schools
• Create Timeline
• Gather Materials""",
                    """<h2>KEY COMPONENTS</h2>
• Personal Essays
• Recommendation Letters
• Test Scores
• Activities List""",
                    """<h2>WRITING TIPS</h2>
• Be Authentic
• Show, Don't Tell
• Start Early
• Get Feedback""",
                    """<h2>FINAL STEPS</h2>
• Double Check Everything
• Meet Deadlines
• Keep Copies
• Follow Up"""
                ]
                add_interaction(session_id, current_state='MAIN_MENU')
                return jsonify({
                    "response": format_response(sections) + "<br><strong>[MAIN_MENU]</strong>"
                })
            else:
                response_text = (
                    "Please select one of these options:<br><br>"
                    "• Explore Careers and Majors<br>"
                    "• Research Colleges<br>"
                    "• Get Application Advice<br>"
                    "<strong>[MAIN_MENU]</strong>"
                )
            
            response_data["response"] = response_text
            return jsonify(response_data)

        elif current_state == 'ASK_CAREER':
            career = validate_career_input(user_message)
            majors_response = call_openai_api_with_retries(f"career in {career}")
    
            if not majors_response:
                return jsonify({
                    "response": "I'm having trouble suggesting majors right now. Please try again.<br><strong>[ASK_CAREER]</strong>"
                })


            majors = parse_majors_list(majors_response)
            if len(majors) != 4:
                return jsonify({
                    "response": "I'm having trouble processing the majors. Please try again.<br><strong>[ASK_CAREER]</strong>"
                })

            add_interaction(session_id, current_state='SHOW_MAJORS', major_selected=", ".join(majors))
            majors_list = "\n".join([f"{i+1}. {m}" for i, m in enumerate(majors, 1)])
    
            response_text = f"""Here are some majors to consider:

        {majors_list}

        <strong>[SHOW_MAJORS]</strong>"""
    
            response_data["response"] = response_text
            return jsonify(response_data)

        elif current_state == 'SHOW_MAJORS':
            print(f"Majors from last interaction: {last_interaction['major_selected']}")
            majors = last_interaction['major_selected'].split(", ")
            print(f"Parsed majors: {majors}")
            selected_major = None
            
            if user_message.isdigit():
                index = int(user_message) - 1
                if 0 <= index < len(majors):
                    selected_major = majors[index]
            elif user_message in majors:
                selected_major = user_message

            if selected_major:
                prompt = f"""Provide detailed information about the {selected_major} major:

<h2>PROGRAM OVERVIEW</h2>
• Program description and focus
• Key features and requirements
• Typical duration

<h2>CORE SKILLS</h2>
• Technical abilities developed
• Professional competencies
• Essential knowledge areas

<h2>COURSEWORK</h2>
• Foundation courses
• Advanced topics
• Available specializations

<h2>CAREER PATHS</h2>
• Entry-level positions
• Career progression
• Industry opportunities"""

                details = call_openai_api(prompt)
                if not details:
                    response_data["response"] = (
                        "I'm having trouble getting information about this major. "
                        "Please try again.<br><strong>[SHOW_MAJORS]</strong>"
                    )
                    return jsonify(response_data)

                add_interaction(session_id, current_state='MAIN_MENU', major_selected=selected_major)
                sections = [section.strip() for section in details.split('<h2>') if section.strip()]
                formatted_sections = [f"<h2>{section}" for section in sections]
                
                response_data["response"] = (
                    format_response(formatted_sections) + 
                    "<br>What else would you like to know?<br><strong>[MAIN_MENU]</strong>"
                )
                return jsonify(response_data)
            else:
                majors_str = "<br>".join([f"{i+1}. {m}" for i, m in enumerate(majors)])
                response_data["response"] = (
                    f"Please select a major from the list:<br><br>{majors_str}<br>"
                    "<strong>[SHOW_MAJORS]</strong>"
                )
                return jsonify(response_data)
        
        elif current_state == 'ASK_COLLEGE':
            college = user_message
            user_majors = get_user_majors(session_id)
            add_interaction(session_id, current_state='MAIN_MENU', college_researched=college)
    
            # First, get basic college information
            basic_prompt = f"""Provide verified information about {college} in this format:

<h2>INSTITUTION OVERVIEW</h2>
- Type: [Public/Private]
- Location: [City, State]
- Total Enrollment: [Approximate number]
- Campus Setting: [Urban/Suburban/Rural]

<h2>ACADEMIC PROFILE</h2>
- Areas of Study
- Notable Programs
- Class Size
- Teaching Focus"""
    
            basic_info = call_openai_api(basic_prompt)
            if not basic_info:
                return jsonify({
                    "response": (
                        f"I apologize, but I need more information about {college}. "
                        "Could you please specify the full name of the institution?<br>"
                        "<strong>[ASK_COLLEGE]</strong>"
                    )
                })
    
            sections = [basic_info]
    
    # Add major-specific information if user has selected majors
            if user_majors:
                for major in user_majors:
                    major_prompt = f"""Information about the {major} program at {college}:

<h2>{major.upper()} PROGRAM</h2>
- Program Availability
- Department Information
- Key Features
- Career Support Services"""
            
                    major_info = call_openai_api(major_prompt)
                    if major_info:
                        sections.append(major_info)
    
    # Add admission information
            admission_prompt = f"""Basic admission information for {college}:

<h2>ADMISSION INFORMATION</h2>
- Application Process
- Key Deadlines
- Required Documents
- Contact Details"""

            admission_info = call_openai_api(admission_prompt)
            if admission_info:
                sections.append(admission_info)
    
    # Format all sections
            formatted_response = format_response([
                section.strip() 
                for section in sections 
                if section and section.strip()
            ])
    
            return jsonify({
                "response": (
                    f"{formatted_response}<br><br>"
                    "What else would you like to know?<br>"
                    "<strong>[MAIN_MENU]</strong>"
                )
            })

    except Exception as e:
        logger.error(f"Error in /chat endpoint: {str(e)}")
        return jsonify({
            "response": "I apologize, but I encountered an error. Please try again.<br><strong>[MAIN_MENU]</strong>",
            "session_id": session_id if 'session_id' in locals() else None
        }), 500

# Additional routes for data management
@app.route('/conversations', methods=['GET'])
def get_conversations():
    """Retrieve all conversation history."""
    try:
        data = load_data()
        return jsonify(data["interactions"]), 200
    except Exception as e:
        logger.error(f"Error in /conversations endpoint: {str(e)}")
        return jsonify({"error": "Failed to retrieve conversations."}), 500

@app.route('/conversations/<string:session_id>', methods=['GET'])
def get_conversation(session_id):
    """Retrieve conversation history for a specific session."""
    try:
        data = load_data()
        interactions = [inter for inter in data["interactions"] if inter["session_id"] == session_id]
        if not interactions:
            return jsonify({"error": "Session not found."}), 404
        return jsonify(interactions), 200
    except Exception as e:
        logger.error(f"Error in /conversations/<session_id> endpoint: {str(e)}")
        return jsonify({"error": "Failed to retrieve conversation."}), 500

@app.route('/conversations/<string:session_id>', methods=['DELETE'])
def delete_conversation(session_id):
    """Delete conversation history for a specific session."""
    try:
        data = load_data()
        initial_length = len(data["interactions"])
        data["interactions"] = [inter for inter in data["interactions"] if inter["session_id"] != session_id]
        final_length = len(data["interactions"])
        save_data(data)
        if initial_length == final_length:
            return jsonify({"error": "Session not found."}), 404
        return jsonify({"message": "Conversation deleted successfully."}), 200
    except Exception as e:
        logger.error(f"Error in DELETE /conversations/<session_id> endpoint: {str(e)}")
        return jsonify({"error": "Failed to delete conversation."}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)