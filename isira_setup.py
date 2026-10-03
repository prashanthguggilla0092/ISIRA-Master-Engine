# -*- coding: utf-8 -*-
"""
ISIRA Master Engine - Neural Architecture V4.0
Developed by Digital Daari for advanced AI-driven architectural solutions.

This Streamlit application integrates Google Cloud's Generative AI (Gemini via Vertex AI),
Speech-to-Text, and Text-to-Speech services with secure credential management
and a dynamic context system powered by Google Sheets.
"""

# --- 0. Core Imports ---
import os
import logging
import streamlit as st
from google.generativeai import types as legacy_genai_types
from googleapiclient.discovery import build
from google.oauth2 import service_account
from datetime import datetime
import streamlit.components.v1 as components
from audio_recorder_streamlit import audio_recorder
import json
import tempfile
import time
import atexit
from PIL import Image
import io

# Native Vertex AI Libraries to prevent Part AttributeErrors
import vertexai
from vertexai.generative_models import GenerativeModel, Part

from google.cloud import speech_v1p1beta1 as speech
from google.cloud import texttospeech as tts_lib

# --- 1. Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logging.info("ISIRA Master Engine: Logging initialized.")

# --- 2. PAGE CONFIG ---
st.set_page_config(page_title="ISIRA Master Engine", layout="wide", initial_sidebar_state="collapsed")
logging.info("Streamlit page configuration set.")

# --- 3. Secrets Management ---
try:
    SPREADSHEET_ID: str = st.secrets["GOOGLE_SHEETS"]["SPREADSHEET_ID"]
    SERVICE_ACCOUNT_INFO: dict = st.secrets["GOOGLE_SHEETS"]["SERVICE_ACCOUNT_KEY"]
    AUTH_USERNAME: str = st.secrets["AUTH"]["USERNAME"]
    AUTH_PASSWORD: str = st.secrets["AUTH"]["PASSWORD"]
    GCP_PROJECT_ID: str = st.secrets["GCP"]["PROJECT_ID"]
    GCP_LOCATION: str = st.secrets["GCP"]["LOCATION"]
except KeyError as e:
    st.error(
        f"CRITICAL CONFIGURATION ERROR: Missing secret key '{e}'. "
        "Please ensure your `.streamlit/secrets.toml` is correctly configured with all required keys."
    )
    logging.critical(f"Missing critical configuration variable in st.secrets: {e}")
    st.stop()

# --- Initialize Gemini Client (Vertex AI Native Framework) ---
try:
    vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)
    logging.info(f"Google GenAI configured via Native Vertex AI wrapper on '{GCP_PROJECT_ID}'.")
except Exception as e:
    st.error(f"CRITICAL ERROR: Failed to configure Gemini with Vertex AI. Details: {e}")
    logging.critical(f"Gemini client initialization failed: {e}")
    st.stop()

_GCP_TEMP_CREDENTIALS_PATH = None

# --- 4. Secure GCP Credential Initialization ---
@st.cache_resource
def _initialize_gcp_environment(_service_account_info_dict: dict):
    global _GCP_TEMP_CREDENTIALS_PATH
    try:
        clean_dict = dict(_service_account_info_dict)
        creds = service_account.Credentials.from_service_account_info(clean_dict)
        logging.info("GCP credentials object created successfully from Streamlit secrets.")
        if _GCP_TEMP_CREDENTIALS_PATH is None:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".json") as temp_file:
                json.dump(clean_dict, temp_file)
            _GCP_TEMP_CREDENTIALS_PATH = temp_file.name
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _GCP_TEMP_CREDENTIALS_PATH
            atexit.register(lambda: os.remove(_GCP_TEMP_CREDENTIALS_PATH) if os.path.exists(_GCP_TEMP_CREDENTIALS_PATH) else None)
            logging.info(f"Temporary GCP credential file created at: {_GCP_TEMP_CREDENTIALS_PATH}")
        else:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _GCP_TEMP_CREDENTIALS_PATH
        return creds
    except Exception as e:
        logging.critical(f"Failed to initialize GCP credentials securely: {e}")
        st.error(f"CRITICAL ERROR: Could not initialize GCP credentials. Details: {e}")
        st.stop()

gcp_credentials = _initialize_gcp_environment(SERVICE_ACCOUNT_INFO)

# --- 5. GCP Clients ---
@st.cache_resource
def load_gcp_clients_with_creds(_credentials: service_account.Credentials):
    try:
        speech_client_instance = speech.SpeechClient(credentials=_credentials)
        tts_client_instance = tts_lib.TextToSpeechClient(credentials=_credentials)
        logging.info("GCP Speech and TTS clients initialized successfully.")
        return speech_client_instance, tts_client_instance
    except Exception as e:
        logging.error(f"Failed to initialize GCP clients: {e}")
        return None, None

speech_client, tts_client = load_gcp_clients_with_creds(gcp_credentials)

# --- 6. Google Sheets Service ---
@st.cache_resource(ttl=3600)
def get_sheets_service_with_creds(_credentials: service_account.Credentials):
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        scoped_creds = _credentials.with_scopes(SCOPES)
        sheets_service_instance = build('sheets', 'v4', credentials=scoped_creds, static_discovery=False)
        logging.info("Google Sheets service authenticated successfully.")
        return sheets_service_instance
    except Exception as e:
        logging.error(f"Failed to initialize Sheets service: {e}")
        return None

sheets_service = get_sheets_service_with_creds(gcp_credentials)

# --- 7. ISIRA System Prompt ---
ISIRA_SYSTEM_PROMPT = """
You are ISIRA AI, a Supreme AI Architect and Senior Python Developer by Digital Daari.
Strictly follow the 50+ architectural rules:
- Provide high-quality, error-free Python code using modular structures.
- Include professional comments and requirements.txt for all projects.
- Use a professional, cinematic, and expert tone.
- Ensure all Google Cloud integrations are optimized.
- Support local Telugu language communication naturally.
- Always provide responses in a professional, structured, and helpful manner.
- Do not make up information; if a detail is not known, state that gracefully.
- Prioritize security, scalability, and maintainability in all architectural recommendations.
- You are capable of analyzing images provided by the user. If an image is provided, analyze its content in the context of the user's query and your architectural expertise.
"""

# --- 8. Google Sheets Helper Functions ---
def get_all_projects() -> list[str]:
    if not sheets_service:
        logging.warning("Sheets service not available for fetching project list. Using fallback.")
        return ["Digital Daari (Fallback)", "Chaitanya AI (Fallback)"]
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range='B2:B'
        ).execute()
        values = result.get('values', [])
        projects = sorted(list(set([row[0].strip() for row in values if row and row[0].strip()])))
        if not projects:
            logging.info("No projects found in Google Sheet. Using fallback.")
            return ["Digital Daari (Empty Sheet)", "Chaitanya AI (Empty Sheet)"]
        return projects
    except Exception as e:
        logging.error(f"Error fetching project list from Google Sheets: {e}")
        return ["Digital Daari (Error)", "Chaitanya AI (Error)"]

def get_sheet_data(project_name: str) -> str:
    if not sheets_service:
        logging.warning("Sheets service not available for fetching project data. Using fallback context.")
        return "You are ISIRA, a Supreme AI Architect. Context Sync Error: Sheets service unavailable."
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range='A:E'
        ).execute()
        values = result.get('values', [])
        for row in values:
            if len(row) > 3 and row[1].strip() == project_name:
                return row[3].strip()
        logging.info(f"No specific context found for project '{project_name}'.")
        return "You are ISIRA, a Supreme AI Architect. No specific project context found."
    except Exception as e:
        logging.error(f"Error fetching sheet data for project '{project_name}': {e}")
        return f"You are ISIRA, a Supreme AI Architect. Context Sync Error: {e}"

def save_lead_to_sheets(project: str, query: str, response: str, image_present: bool = False) -> None:
    if not sheets_service:
        logging.warning("Sheets service not available for saving lead data.")
        return
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        truncated_response = response[:4000] + "..." if len(response) > 4000 else response
        query_display = f"[IMAGE] {query}" if image_present and query else query
        query_display = "[IMAGE ONLY]" if image_present and not query else query_display
        values = [[timestamp, project, query_display, truncated_response]]
        body = {'values': values}
        sheets_service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range='Leads!A:D',
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        logging.info(f"Lead saved to Google Sheets for project '{project}'.")
    except Exception as e:
        logging.error(f"Error saving lead to Google Sheets: {e}")

# --- 9. 3D Header (Three.js) ---
def add_3d_header():
    three_js_code = """
    <div id="three-container" style="width: 100%; height: 250px; overflow: hidden; margin-top: -50px;"></div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script>
        const container = document.getElementById('three-container');
        if (container) {
            const scene = new THREE.Scene();
            const camera = new THREE.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.1, 1000);
            const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
            renderer.setSize(container.clientWidth, container.clientHeight);
            container.appendChild(renderer.domElement);
            const geometry = new THREE.IcosahedronGeometry(1.8, 1);
            const material = new THREE.MeshBasicMaterial({ color: 0x00ffcc, wireframe: true });
            const sphere = new THREE.Mesh(geometry, material);
            scene.add(sphere);
            camera.position.z = 4;
            function animate() {
                requestAnimationFrame(animate);
                sphere.rotation.x += 0.005;
                sphere.rotation.y += 0.01;
                renderer.render(scene, camera);
            }
            animate();
            window.addEventListener('resize', () => {
                if (container.clientWidth && container.clientHeight) {
                    renderer.setSize(container.clientWidth, container.clientHeight);
                    camera.aspect = container.clientWidth / container.clientHeight;
                    camera.updateProjectionMatrix();
                }
            });
        }
    </script>
    """
    components.html(three_js_code, height=250)

# --- 10. Security Layer (Login) ---
def check_password() -> bool:
    if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
        st.markdown("""
            <style>
            .stApp { background-color: #050505; color: #ffffff; font-family: monospace; }
            .stTextInput label { color: #ffffff !important; }
            input { background-color: #000 !important; color: #00ffcc !important; border: 1px solid #00ffcc !important; border-radius: 8px !important; }
            .stButton > button { background: #00ffcc !important; color: #000 !important; font-weight: bold !important; width: 100%; border-radius: 8px !important; }
            </style>
            """, unsafe_allow_html=True)
        st.markdown(
            "<h1 style='text-align: center; color: #00ffcc; text-shadow: 0 0 15px #00ffcc; margin-top: 50px;'>ISIRA ACCESS CONTROL</h1>",
            unsafe_allow_html=True
        )
        with st.form("login_form"):
            col1, col2, col3 = st.columns([1, 1.5, 1])
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                username_input = st.text_input("ARCHITECT_ID", key="login_username")
                password_input = st.text_input("ACCESS_CODE", type="password", key="login_password")
                submitted = st.form_submit_button("AUTHORIZE")
                if submitted:
                    if username_input == AUTH_USERNAME and password_input == AUTH_PASSWORD:
                        st.session_state["password_correct"] = True
                        st.success("ACCESS GRANTED. Initializing Neural Interface...")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("ACCESS DENIED. Invalid ARCHITECT_ID or ACCESS_CODE.")
        return False
    return True

# --- 11. Speech & TTS Functions ---
def transcribe_audio_gcp(audio_bytes: bytes) -> str:
    if not speech_client:
        logging.error("Speech-to-Text client not initialized.")
        return "ERROR: Speech-to-Text service unavailable."
    audio = speech.RecognitionAudio(content=audio_bytes)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
        sample_rate_hertz=48000,
        language_code="te-IN",
        enable_automatic_punctuation=True,
    )
    try:
        response = speech_client.recognize(config=config, audio=audio)
        if response.results:
            return response.results[0].alternatives[0].transcript
        logging.info("No transcription results found for audio.")
        return ""
    except Exception as e:
        logging.error(f"Google Cloud Speech-to-Text error during transcription: {e}")
        return f"ERROR: Could not transcribe audio. Details: {e}"

def synthesize_speech_gcp(text: str, language_code: str = "te-IN") -> bytes:
    if not tts_client:
        logging.error("Text-to-Speech client not initialized.")
        return b""
    input_text = tts_lib.SynthesisInput(text=text)
    voice = tts_lib.VoiceSelectionParams(
        language_code=language_code,
        name="te-IN-Wavenet-A",
        ssml_gender=tts_lib.SsmlVoiceGender.FEMALE,
    )
    audio_config = tts_lib.AudioConfig(audio_encoding=tts_lib.AudioEncoding.MP3)
    try:
        response = tts_client.synthesize_speech(
            input=input_text, voice=voice, audio_config=audio_config
        )
        return response.audio_content
    except Exception as e:
        logging.error(f"Google Cloud Text-to-Speech error during synthesis: {e}")
        return b""

# --- 12. Main Application ---
def main_app():

    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Syncopate:wght@700&family=Space+Grotesk:wght=300;500&display=swap');

        .stApp {
            background: radial-gradient(circle at top right, #001a1a, #000000);
            color: #ffffff;
            font-family: 'Space Grotesk', sans-serif;
        }

        .cinema-title {
            font-family: 'Syncopate', sans-serif;
            font-size: 3rem;
            text-align: center;
            letter-spacing: 12px;
            background: linear-gradient(90deg, #00ffcc, #ffffff, #00ffcc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-size: 200% auto;
            animation: shine 4s linear infinite;
            margin-top: -30px;
        }

        @keyframes shine {
            to { background-position: 200% center; }
        }

        .response-box {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 20px;
            padding: 20px;
            border-left: 3px solid #00ffcc;
            margin-bottom: 15px;
            color: #ffffff !important;
            font-size: 1.1rem !important;
            line-height: 1.6 !important;
            white-space: pre-wrap;
            word-wrap: break-word;
        }

        .user-message-box {
            background: rgba(0, 0, 0, 0.2);
            border-left-color: #ffffff;
        }

        /* ── Absolute WhatsApp Wrapper Structure ── */
        .whatsapp-layout-wrapper {
            position: fixed;
            bottom: 20px;
            left: 5%;
            width: 90%;
            z-index: 9999;
            display: block !important;
        }

        /* ── TRUE WHATSAPP WEBPACK FLEX CAPSULE BAR (Strict Single Row Aligned) ── */
        .whatsapp-capsule-bar {
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important;
            background: #ffffff !important; 
            border: 1px solid rgba(0, 0, 0, 0.08) !important;
            border-radius: 35px !important;
            padding: 4px 16px !important;
            width: 100% !important;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2) !important;
            gap: 10px !important;
        }

        /* Pure Vertical Alignment & Block Corrections Inside Container */
        .flex-plus-segment, .flex-input-segment, .flex-mic-segment {
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        
        .flex-input-segment {
            flex-grow: 1 !important;
        }

        /* Force Override Streamlit's structural block margins */
        .whatsapp-capsule-bar div[data-testid="stVerticalBlock"],
        .whatsapp-capsule-bar div[data-testid="element-container"] {
            margin: 0px !important;
            padding: 0px !important;
            width: auto !important;
        }

        .whatsapp-capsule-bar .flex-input-segment div[data-testid="element-container"] {
            width: 100% !important;
        }

        /* Clean Native Input Injection Styling Rules */
        .flex-input-segment .stTextInput input {
            color: #111b21 !important;
            background-color: transparent !important;
            border: none !important;
            font-size: 1.05rem !important;
            padding: 8px 4px !important;
            width: 100% !important;
        }
        .flex-input-segment .stTextInput > div, 
        .flex-input-segment .stTextInput > div > div {
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
            width: 100% !important;
        }

        /* Minimal Plus Action Icon Overrides */
        .flex-plus-segment .stButton button {
            background: transparent !important;
            color: #54656f !important;
            border: none !important;
            font-size: 2rem !important;
            font-weight: 300 !important;
            padding: 0px !important;
            margin: 0px !important;
            width: 35px !important;
            height: 35px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            box-shadow: none !important;
        }
        .flex-plus-segment .stButton button:hover {
            color: #00a884 !important;
            transform: scale(1.1);
            background: transparent !important;
        }

        /* Micro Audio Streamlit Wrapper Component Polish */
        .flex-mic-segment div {
            display: flex !important;
            align-items: center !important;
        }

        /* ── POPUP MENU BOX EXACT WHATSAPP SPECIFICATIONS ── */
        .whatsapp-popup-menu {
            background-color: #ffffff !important;
            border-radius: 16px !important;
            padding: 6px 0px !important;
            width: 220px !important;
            position: absolute !important;
            bottom: 60px !important;
            left: 10px !important;
            z-index: 100000 !important;
            box-shadow: 0px 8px 24px rgba(0,0,0,0.2) !important;
        }

        .whatsapp-menu-item .stButton button {
            background: transparent !important;
            color: #3b4a54 !important;
            border: none !important;
            width: 100% !important;
            text-align: left !important;
            padding: 10px 20px !important;
            font-family: 'Space Grotesk', sans-serif !important;
            font-weight: 500 !important;
            font-size: 0.95rem !important;
            border-radius: 0px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: flex-start !important;
            box-shadow: none !important;
        }
        .whatsapp-menu-item .stButton button:hover {
            background-color: #f5f6f6 !important;
            color: #111b21 !important;
        }

        .stSelectbox > label,
        .stTextInput > label {
            color: #00ffcc !important;
            font-family: 'Syncopate', sans-serif;
            font-size: 0.8rem;
            letter-spacing: 2px;
        }

        [data-testid="stHeader"] {
            display: none !important;
            visibility: hidden !important;
        }

        /* Status chips */
        .isira-status-chip {
            font-size: 0.7rem;
            color: #00ffcc;
            background: rgba(0,255,204,0.1);
            border: 1px solid rgba(0,255,204,0.3);
            border-radius: 20px;
            padding: 3px 10px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }

        /* Upload panel dropzone styling */
        .upload-panel [data-testid="stFileUploaderDropzone"] {
            border: 1px solid rgba(0,255,204,0.4) !important;
            border-radius: 14px !important;
            background: rgba(0,255,204,0.04) !important;
        }
        .upload-panel [data-testid="stFileUploaderDropzone"] svg {
            color: #00ffcc !important;
        }

        /* Camera panel styling */
        .camera-panel [data-testid="stCameraInput"] > div {
            border-radius: 16px !important;
            border: 1px solid rgba(0,255,204,0.3) !important;
        }
        .camera-panel label { display: none !important; }
        
        /* Spacing for content to not get hidden behind fixed footer */
        .chat-content-container {
            margin-bottom: 120px;
        }
        </style>
    """, unsafe_allow_html=True)

    add_3d_header()

    st.markdown("<h1 class='cinema-title'>ISIRA</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='text-align:center; letter-spacing:5px; opacity:0.5; font-size:0.7rem;'>"
        "NEURAL ARCHITECTURE V4.0 // VERTEX AI INTEGRATED // MULTIMODAL"
        "</p>",
        unsafe_allow_html=True
    )

    # --- Session State Initialization ---
    if "messages" not in st.session_state: st.session_state.messages = []
    if "selected_project" not in st.session_state: st.session_state.selected_project = None
    if "current_context" not in st.session_state: st.session_state.current_context = ""
    if "chat_history" not in st.session_state: st.session_state.chat_history = []
    if "last_uploaded_bytes" not in st.session_state: st.session_state.last_uploaded_bytes = None
    if "last_camera_bytes" not in st.session_state: st.session_state.last_camera_bytes = None
    if "last_audio_bytes" not in st.session_state: st.session_state.last_audio_bytes = None
    if "last_processed_audio" not in st.session_state: st.session_state.last_processed_audio = None
    if "voice_text" not in st.session_state: st.session_state.voice_text = ""
    if "uploaded_image_data" not in st.session_state: st.session_state.uploaded_image_data = None
    if "captured_image_data" not in st.session_state: st.session_state.captured_image_data = None
    if "uploaded_image_mime" not in st.session_state: st.session_state.uploaded_image_mime = None
    if "has_image_input_this_turn" not in st.session_state: st.session_state.has_image_input_this_turn = False
    if "show_camera" not in st.session_state: st.session_state.show_camera = False
    if "show_upload" not in st.session_state: st.session_state.show_upload = False
    if "show_plus_panel" not in st.session_state: st.session_state.show_plus_panel = False

    # --- Sidebar ---
    with st.sidebar:
        st.markdown("<h2 style='color:#00ffcc;'>PROJECT INTERFACE</h2>", unsafe_allow_html=True)
        projects = get_all_projects()
        initial_index = 0

        if st.session_state.selected_project in projects:
            initial_index = projects.index(st.session_state.selected_project)
        elif not st.session_state.selected_project and projects:
            st.session_state.selected_project = projects[0]
            initial_index = 0

        selected_project_name = st.selectbox(
            "Select Project Context:",
            options=projects,
            index=initial_index,
            key="project_selector",
            help="Choose a project to load its specific context for ISIRA."
        )

        if selected_project_name != st.session_state.selected_project or not st.session_state.current_context:
            st.session_state.selected_project = selected_project_name
            project_context = get_sheet_data(selected_project_name)
            st.session_state.current_context = ISIRA_SYSTEM_PROMPT + "\n\n" + project_context
            st.session_state.messages = []
            st.session_state.chat_history = []
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"Project context for '{selected_project_name}' loaded. How may I assist you, Architect?"
            })
            st.session_state.uploaded_image_data = None
            st.session_state.captured_image_data = None
            st.session_state.uploaded_image_mime = None
            st.session_state.has_image_input_this_turn = False
            st.session_state.last_uploaded_bytes = None
            st.session_state.last_camera_bytes = None
            st.session_state.last_audio_bytes = None
            st.session_state.last_processed_audio = None
            st.session_state.voice_text = ""
            st.session_state.show_camera = False
            st.session_state.show_upload = False
            st.session_state.show_plus_panel = False
            st.rerun()

        st.markdown("---")
        st.markdown("<h3 style='color:#00ffcc;'>ISIRA Status: Online</h3>", unsafe_allow_html=True)
        st.write(f"Project: **{st.session_state.selected_project or 'None'}**")
        st.write("Model: `gemini-2.5-flash`")
        st.write("Language: `Telugu (te-IN)`")
        st.write(f"GCP Project: `{GCP_PROJECT_ID}`")
        st.markdown("---")

        if st.button("Clear Chat History", key="clear_chat_button"):
            st.session_state.messages = []
            st.session_state.chat_history = []
            st.session_state.uploaded_image_data = None
            st.session_state.uploaded_image_mime = None
            st.session_state.captured_image_data = None
            st.session_state.has_image_input_this_turn = False
            st.session_state.last_uploaded_bytes = None
            st.session_state.last_camera_bytes = None
            st.session_state.last_audio_bytes = None
            st.session_state.last_processed_audio = None
            st.session_state.voice_text = ""
            st.session_state.show_camera = False
            st.session_state.show_upload = False  
            st.session_state.show_plus_panel = False
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Chat history cleared. Awaiting your next directive, Architect."
            })
            st.rerun()

    # --- Chat Display Wrapper Container ---
    st.markdown('<div class="chat-content-container">', unsafe_allow_html=True)
    for message in st.session_state.messages:
        role_class = "user-message-box" if message["role"] == "user" else ""
        with st.chat_message(message["role"]):
            if "image_data" in message and message["image_data"] is not None:
                st.image(message["image_data"], caption="User Input Image", width=200)
            st.markdown(
                f"<div class='response-box {role_class}'>{message['content']}</div>",
                unsafe_allow_html=True
            )
            if message["role"] == "assistant" and "audio" in message:
                st.audio(message["audio"], format='audio/mp3')
    st.markdown('</div>', unsafe_allow_html=True)

    # --- Active Status Indicators Above Input ---
    chips = []
    if st.session_state.voice_text: chips.append("🎙️ Voice ready")
    if st.session_state.uploaded_image_data: chips.append("🖼️ Image loaded")
    if st.session_state.captured_image_data: chips.append("📷 Photo captured")
    if chips:
        chip_html = " &nbsp; ".join(f"<span class='isira-status-chip'>{c}</span>" for c in chips)
        st.markdown(f"<div style='display:flex;gap:6px;align-items:center;padding-bottom:8px;position:fixed;bottom:75px;left:5%;z-index:9998;'>{chip_html}</div>", unsafe_allow_html=True)


    # ═══════════════════════════════════════════════════════════════
    # --- FIXED WHATSAPP WEB STYLE CONTROLS LAYOUT FRAME ---
    # ═══════════════════════════════════════════════════════════════
    st.markdown('<div class="whatsapp-layout-wrapper">', unsafe_allow_html=True)

    # 1. Authentic White Pop-up Menu Layer
    if st.session_state.show_plus_panel:
        st.markdown('<div class="whatsapp-popup-menu">', unsafe_allow_html=True)

        st.markdown('<div class="whatsapp-menu-item">', unsafe_allow_html=True)
        if st.button("📄 &nbsp; Document", key="wa_doc_item_btn"):
            st.session_state.show_upload = True
            st.session_state.show_camera = False
            st.session_state.show_plus_panel = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="whatsapp-menu-item">', unsafe_allow_html=True)
        if st.button("🖼️ &nbsp; Photos & videos", key="wa_photos_item_btn"):
            st.session_state.show_upload = True
            st.session_state.show_camera = False
            st.session_state.show_plus_panel = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="whatsapp-menu-item">', unsafe_allow_html=True)
        if st.button("📷 &nbsp; Camera", key="wa_camera_item_btn"):
            st.session_state.show_camera = True
            st.session_state.show_upload = False
            st.session_state.show_plus_panel = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # --- NEW ADDITION: Voice Message Option ---
        st.markdown('<div class="whatsapp-menu-item">', unsafe_allow_html=True)
        if st.button("🎙️ &nbsp; Voice Message", key="wa_voice_item_btn"):
            st.session_state.show_plus_panel = False # Close the menu
            st.session_state.voice_text = "" # Clear any pending voice text
            st.session_state.show_camera = False # Ensure camera/upload panels are hidden
            st.session_state.show_upload = False
            st.rerun() # Rerun to update UI and hide the panel
        st.markdown('</div>', unsafe_allow_html=True)
        # --- END NEW ADDITION ---

        st.markdown('</div>', unsafe_allow_html=True)

    # 2. Main High-Integrity Flexbox Capsule Bar
    st.markdown('<div class="whatsapp-capsule-bar">', unsafe_allow_html=True)

    # Plus Segment Frame
    st.markdown('<div class="flex-plus-segment">', unsafe_allow_html=True)
    if st.button("+", key="plus_expand_contract_btn"):
        st.session_state.show_plus_panel = not st.session_state.show_plus_panel
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Core Message Input Box Segment Frame
    voice_prefill = st.session_state.voice_text
    st.markdown('<div class="flex-input-segment">', unsafe_allow_html=True)
    user_input = st.text_input(
        label="Chat Input Field",
        value="",
        placeholder="Type a message..." if not voice_prefill else voice_prefill,
        key="chat_input_field",
        label_visibility="collapsed"
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # Microphone Widget Segment Frame (remains here for direct access)
    st.markdown('<div class="flex-mic-segment">', unsafe_allow_html=True)
    audio_bytes = audio_recorder(
        text="",
        recording_color="#25D366", # WhatsApp Web Brand Green
        neutral_color="#a6aab0",
        icon_name="microphone",
        icon_size="lg",
        key="audio_recorder_widget"
    )
    if audio_bytes and len(audio_bytes) > 5000:
        if audio_bytes != st.session_state.get("last_processed_audio"):
            st.session_state["last_processed_audio"] = audio_bytes
            with st.spinner("🎙️ Transcribing..."):
                transcribed = transcribe_audio_gcp(audio_bytes)
            if transcribed and not transcribed.startswith("ERROR"):
                st.session_state["voice_text"] = transcribed
                st.rerun()
            else:
                st.warning("Audio processing failed.")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True) # Closes whatsapp-capsule-bar
    st.markdown('</div>', unsafe_allow_html=True) # Closes whatsapp-layout-wrapper


    # ── Upload panel dropzone activation ──
    if st.session_state.show_upload:
        st.markdown("<div class='upload-panel' style='position:fixed; bottom:85px; left:5%; width:90%; z-index:9997;'>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader(
            "Choose Image",
            type=["jpg", "jpeg", "png", "webp"],
            key="image_uploader",
            label_visibility="collapsed"
        )
        st.markdown("</div>", unsafe_allow_html=True)
        if uploaded_file is not None:
            img_bytes = uploaded_file.read()
            if img_bytes != st.session_state.last_uploaded_bytes:
                st.session_state.last_uploaded_bytes = img_bytes
                st.session_state.uploaded_image_data = img_bytes
                st.session_state.uploaded_image_mime = uploaded_file.type
                st.session_state.has_image_input_this_turn = True
                st.session_state.show_upload = False   
                st.rerun()

    # ── Camera panel activation zone ──
    if st.session_state.show_camera:
        st.markdown("<div class='camera-panel' style='position:fixed; bottom:85px; left:5%; width:90%; z-index:9997;'>", unsafe_allow_html=True)
        camera_photo = st.camera_input("Take Photo", key="camera_widget", label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)
        if camera_photo is not None:
            cam_bytes = camera_photo.read()
            if cam_bytes != st.session_state.last_camera_bytes:
                st.session_state.last_camera_bytes = cam_bytes
                st.session_state.captured_image_data = cam_bytes
                st.session_state.uploaded_image_mime = "image/jpeg"
                st.session_state.has_image_input_this_turn = True
                st.session_state.show_camera = False   
                st.rerun()

    # Asset Previews displayed underneath the unified capsule layout bar
    if st.session_state.uploaded_image_data or st.session_state.captured_image_data:
        st.markdown("<br>", unsafe_allow_html=True)
        prev_col1, prev_col2, _ = st.columns([1, 1, 8])
        with prev_col1:
            if st.session_state.uploaded_image_data:
                st.image(st.session_state.uploaded_image_data, width=60, caption="Upload")
        with prev_col2:
            if st.session_state.captured_image_data:
                st.image(st.session_state.captured_image_data, width=60, caption="Camera")

    # Final Execution Input Router Management
    final_input = ""
    if user_input:
        final_input = user_input
        st.session_state.voice_text = ""
    elif voice_prefill and not user_input:
        final_input = voice_prefill
        st.session_state.voice_text = ""

    # ═══════════════════════════════════════════════════════════════
    # --- Main Neural Process Execution Layer ---
    # ═══════════════════════════════════════════════════════════════
    if final_input or st.session_state.has_image_input_this_turn:
        active_image_data = st.session_state.captured_image_data or st.session_state.uploaded_image_data
        active_image_mime = st.session_state.uploaded_image_mime or "image/jpeg"
        has_image = active_image_data is not None

        display_text = final_input if final_input else "[Image structure data frame shared]"

        st.session_state.messages.append({
            "role": "user",
            "content": display_text,
            "image_data": active_image_data if has_image else None
        })

        current_turn_parts = []
        if has_image:
            current_turn_parts.append(
                Part.from_bytes(data=active_image_data, mime_type=active_image_mime)
            )
        if final_input:
            current_turn_parts.append(final_input)

        st.session_state.chat_history.append({"role": "user", "parts": current_turn_parts})

        with st.chat_message("assistant"):
            with st.spinner("ISIRA is processing..."):
                try:
                    model_instance = GenerativeModel(
                        model_name="gemini-2.5-flash",
                        system_instruction=st.session_state.current_context
                    )
                    response = model_instance.generate_content(
                        contents=st.session_state.chat_history,
                        generation_config={
                            "max_output_tokens": 8192,
                            "temperature": 0.7,
                        }
                    )
                    isira_response = response.text
                    st.session_state.chat_history.append({"role": "model", "parts": [isira_response]})

                    audio_response = synthesize_speech_gcp(isira_response[:3000])

                    msg = {"role": "assistant", "content": isira_response}
                    if audio_response:
                        msg["audio"] = audio_response
                    st.session_state.messages.append(msg)

                    save_lead_to_sheets(
                        project=st.session_state.selected_project or "Unknown",
                        query=final_input or "",
                        response=isira_response,
                        image_present=has_image
                    )
                    
                    st.session_state.show_plus_panel = False
                    st.rerun()

                except Exception as e:
                    err_msg = f"ISIRA Engine Error: {e}"
                    logging.error(err_msg)
                    st.error(err_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": err_msg
                    })

        # --- Reset Image State ---
        st.session_state.uploaded_image_data = None
        st.session_state.captured_image_data = None
        st.session_state.uploaded_image_mime = None
        st.session_state.has_image_input_this_turn = False

    st.markdown(
        "<p style='text-align: center; opacity: 0.2; font-size: 0.7rem; margin-top: 40px; margin-bottom: 80px;'>"
        "© 2026 DIGITAL DAARI // ARCHITECTURAL INTEGRITY VERIFIED"
        "</p>",
        unsafe_allow_html=True
    )

# --- Entry Point ---
if __name__ == "__main__":
    if check_password():
        main_app()