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
import urllib.parse # For URL encoding/decoding

# Native Vertex AI Libraries
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
        "Please ensure your `.streamlit/secrets.toml` is correctly configured."
    )
    logging.critical(f"Missing critical configuration variable: {e}")
    st.stop()

# --- Initialize Vertex AI ---
try:
    vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)
    logging.info(f"Vertex AI initialized on '{GCP_PROJECT_ID}'.")
except Exception as e:
    st.error(f"CRITICAL ERROR: Failed to configure Vertex AI. Details: {e}")
    st.stop()

_GCP_TEMP_CREDENTIALS_PATH = None

# --- 4. GCP Credential Initialization ---
@st.cache_resource
def _initialize_gcp_environment(_service_account_info_dict: dict):
    global _GCP_TEMP_CREDENTIALS_PATH
    try:
        clean_dict = dict(_service_account_info_dict)
        creds = service_account.Credentials.from_service_account_info(clean_dict)
        if _GCP_TEMP_CREDENTIALS_PATH is None:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".json") as temp_file:
                json.dump(clean_dict, temp_file)
            _GCP_TEMP_CREDENTIALS_PATH = temp_file.name
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _GCP_TEMP_CREDENTIALS_PATH
            atexit.register(
                lambda: os.remove(_GCP_TEMP_CREDENTIALS_PATH)
                if os.path.exists(_GCP_TEMP_CREDENTIALS_PATH) else None
            )
        else:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _GCP_TEMP_CREDENTIALS_PATH
        return creds
    except Exception as e:
        logging.critical(f"Failed to initialize GCP credentials: {e}")
        st.error(f"CRITICAL ERROR: Could not initialize GCP credentials. Details: {e}")
        st.stop()

gcp_credentials = _initialize_gcp_environment(SERVICE_ACCOUNT_INFO)

# --- 5. GCP Clients ---
@st.cache_resource
def load_gcp_clients_with_creds(_credentials):
    try:
        speech_client_instance = speech.SpeechClient(credentials=_credentials)
        tts_client_instance = tts_lib.TextToSpeechClient(credentials=_credentials)
        return speech_client_instance, tts_client_instance
    except Exception as e:
        logging.error(f"Failed to initialize GCP clients: {e}")
        return None, None

speech_client, tts_client = load_gcp_clients_with_creds(gcp_credentials)

# --- 6. Google Sheets Service ---
@st.cache_resource(ttl=3600)
def get_sheets_service_with_creds(_credentials):
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        scoped_creds = _credentials.with_scopes(SCOPES)
        return build('sheets', 'v4', credentials=scoped_creds, static_discovery=False)
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
- You are capable of analyzing images provided by the user.
"""

# --- 8. Google Sheets Helpers ---
def get_all_projects() -> list:
    if not sheets_service:
        return ["Digital Daari (Fallback)", "Chaitanya AI (Fallback)"]
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range='B2:B'
        ).execute()
        values = result.get('values', [])
        projects = sorted(list(set([row[0].strip() for row in values if row and row[0].strip()])))
        return projects if projects else ["Digital Daari (Empty Sheet)"]
    except Exception as e:
        logging.error(f"Error fetching projects: {e}")
        return ["Digital Daari (Error)"]

def get_sheet_data(project_name: str) -> str:
    if not sheets_service:
        return "You are ISIRA, a Supreme AI Architect. Context Sync Error."
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range='A:E'
        ).execute()
        values = result.get('values', [])
        for row in values:
            if len(row) > 3 and row[1].strip() == project_name:
                return row[3].strip()
        return "You are ISIRA, a Supreme AI Architect. No specific context found."
    except Exception as e:
        return f"You are ISIRA, a Supreme AI Architect. Context Error: {e}"

def save_lead_to_sheets(project: str, query: str, response: str, image_present: bool = False):
    if not sheets_service:
        return
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        truncated = response[:4000] + "..." if len(response) > 4000 else response
        q_display = f"[IMAGE] {query}" if image_present and query else query
        q_display = "[IMAGE ONLY]" if image_present and not query else q_display
        body = {'values': [[timestamp, project, q_display, truncated]]}
        sheets_service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range='Leads!A:D',
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
    except Exception as e:
        logging.error(f"Error saving lead: {e}")


# --- 9. Login ---
def check_password() -> bool:
    if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
        st.markdown("""
            <style>
            .stApp { background-color: #050505; color: #ffffff; font-family: monospace; }
            .stTextInput label { color: #ffffff !important; }
            input { background-color: #000 !important; color: #00ffcc !important;
                    border: 1px solid #00ffcc !important; border-radius: 8px !important; }
            .stButton > button { background: #00ffcc !important; color: #000 !important;
                                 font-weight: bold !important; width: 100%; border-radius: 8px !important; }
            </style>""", unsafe_allow_html=True)
        st.markdown(
            "<h1 style='text-align:center;color:#00ffcc;text-shadow:0 0 15px #00ffcc;margin-top:50px;'>"
            "ISIRA ACCESS CONTROL</h1>",
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
                        st.error("ACCESS DENIED.")
        return False
    return True

# --- 10. Speech & TTS ---
def transcribe_audio_gcp(audio_bytes: bytes) -> str:
    if not speech_client:
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
        return ""
    except Exception as e:
        return f"ERROR: {e}"

def synthesize_speech_gcp(text: str, language_code: str = "te-IN") -> bytes:
    if not tts_client:
        return b""
    try:
        input_text = tts_lib.SynthesisInput(text=text)
        voice = tts_lib.VoiceSelectionParams(
            language_code=language_code,
            name="te-IN-Wavenet-A",
            ssml_gender=tts_lib.SsmlVoiceGender.FEMALE,
        )
        audio_config = tts_lib.AudioConfig(audio_encoding=tts_lib.AudioEncoding.MP3)
        response = tts_client.synthesize_speech(input=input_text, voice=voice, audio_config=audio_config)
        return response.audio_content
    except Exception as e:
        logging.error(f"TTS error: {e}")
        return b""

# ══════════════════════════════════════════════════════════════════════
# --- 11. Main Application ---
# ══════════════════════════════════════════════════════════════════════
def main_app():

    # ── 1. CLEAN & BULLETPROOF BACKGROUND INJECTION ──
    components.html("""
        <script>
            const parentDoc = window.parent.document;

            // --- Cleanup existing background & Three.js instances ---
            const existingBg = parentDoc.getElementById('isira-cyber-bg');
            if (existingBg) { existingBg.remove(); }

            // --- Inject Background Div ---
            const bg = parentDoc.createElement('div');
            bg.id = 'isira-cyber-bg';
            bg.style.position = 'fixed';
            bg.style.top = '0';
            bg.style.left = '0';
            bg.style.width = '100vw';
            bg.style.height = '100vh';
            bg.style.zIndex = '-9999';
            bg.style.backgroundColor = '#000000';
            bg.style.pointerEvents = 'none';
            parentDoc.body.appendChild(bg);

            // --- Load Three.js if not already loaded and initialize ---
            if (!window.parent.THREE) {
                const script = parentDoc.createElement('script');
                script.src = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js';
                script.onload = () => { initThree(bg); };
                parentDoc.head.appendChild(script);
            } else {
                initThree(bg);
            }

            function initThree(targetDiv) {
                const THREE = window.parent.THREE;
                const scene = new THREE.Scene();
                const camera = new THREE.PerspectiveCamera(60, window.parent.innerWidth / window.parent.innerHeight, 0.1, 1000);
                const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });

                renderer.setSize(window.parent.innerWidth, window.parent.innerHeight);
                targetDiv.appendChild(renderer.domElement);

                const geometry = new THREE.IcosahedronGeometry(2.2, 1);
                const material = new THREE.MeshBasicMaterial({ 
                    color: 0x00ffcc, 
                    wireframe: true,
                    transparent: true,
                    opacity: 0.25
                });
                const mesh = new THREE.Mesh(geometry, material);
                scene.add(mesh);

                camera.position.z = 5;

                function animate() {
                    window.parent.requestAnimationFrame(animate);
                    mesh.rotation.x += 0.002;
                    mesh.rotation.y += 0.005;
                    renderer.render(scene, camera);
                }
                animate();

                window.parent.addEventListener('resize', () => {
                    camera.aspect = window.parent.innerWidth / window.parent.innerHeight;
                    camera.updateProjectionMatrix();
                    renderer.setSize(window.parent.innerWidth, window.parent.innerHeight);
                });
            }
        </script>
    """, height=0)

    # ── 2. GLOBAL CSS ──
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Syncopate:wght@700&family=Space+Grotesk:wght@300;500&display=swap');

        .stApp {
            background: rgba(0, 10, 10, 0.6) !important;
            color: #ffffff !important;
            font-family: 'Space Grotesk', sans-serif;
        }

        [data-testid="stHeader"] { display: none !important; }

        .stApp p, .stApp span, .stApp label, .stApp h1, .stApp h2, .stApp h3 {
            color: #ffffff !important;
            opacity: 1 !important;
            visibility: visible !important;
        }

        [data-testid="stSidebar"] {
            background-color: rgba(5, 15, 15, 0.95) !important;
        }

        div[data-baseweb="select"] * {
            color: #00ffcc !important;
        }

        .stApp > div:first-child > div:first-child > div:first-child {
            padding-bottom: 120px;
        }

        /* ── Cinema Title ── */
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
            margin-top: 20px;
            color: transparent !important;
        }
        @keyframes shine { to { background-position: 200% center; } }

        /* ── Chat Bubbles ── */
        .response-box {
            background: rgba(15, 35, 35, 0.8) !important;
            backdrop-filter: blur(8px);
            border-radius: 20px;
            padding: 20px;
            border-left: 3px solid #00ffcc;
            margin-bottom: 15px;
            color: #ffffff !important;
            font-size: 1.1rem !important;
            line-height: 1.6 !important;
        }
        .user-message-box { 
            border-left-color: #ffffff; 
            background: rgba(0, 0, 0, 0.7) !important; 
        }

        .isira-status-chip {
            background: rgba(0,255,204,0.15);
            border: 1px solid #00ffcc;
            border-radius: 20px;
            padding: 4px 12px;
            font-size: 0.8rem;
            color: #00ffcc;
        }

        /* ── Hide Streamlit default bottom bar ── */
        div[data-testid="stBottom"] { display: none !important; }

        </style>
    """, unsafe_allow_html=True)

    # ── 3. CINEMA HEADERS ──
    st.markdown("<h1 class='cinema-title'>ISIRA</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='text-align:center;letter-spacing:5px;opacity:0.5;font-size:0.7rem;color:#ffffff;'>"
        "NEURAL ARCHITECTURE V4.0 // VERTEX AI INTEGRATED // MULTIMODAL</p>",
        unsafe_allow_html=True
    )

    # ── Session State Defaults ──
    defaults = {
        "messages": [],
        "selected_project": None,
        "current_context": "",
        "chat_history": [],
        "last_uploaded_bytes": None,
        "last_camera_bytes": None,
        "last_processed_audio": None,
        "voice_text": "",
        "uploaded_image_data": None,
        "captured_image_data": None,
        "uploaded_image_mime": None,
        "has_image_input_this_turn": False,
        "show_camera": False,
        "show_upload": False,
        "show_voice": False,
        "show_plus_panel": False, 
        "pending_input": "",
        "input_submitted": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # ── Sidebar ──
    with st.sidebar:
        st.markdown("<h2 style='color:#00ffcc;font-family:sans-serif;'>PROJECT INTERFACE</h2>", unsafe_allow_html=True)
        projects = get_all_projects()
        initial_index = 0
        if st.session_state.selected_project in projects:
            initial_index = projects.index(st.session_state.selected_project)
        elif not st.session_state.selected_project and projects:
            st.session_state.selected_project = projects[0]

        selected_project_name = st.selectbox(
            "Select Project Context:",
            options=projects,
            index=initial_index,
            key="project_selector",
        )

        if selected_project_name != st.session_state.selected_project or not st.session_state.current_context:
            st.session_state.selected_project = selected_project_name
            project_context = get_sheet_data(selected_project_name)
            st.session_state.current_context = ISIRA_SYSTEM_PROMPT + "\n\n" + project_context
            for k in ["messages","chat_history","uploaded_image_data","captured_image_data",
                       "uploaded_image_mime","has_image_input_this_turn","last_uploaded_bytes",
                       "last_camera_bytes","last_processed_audio","voice_text",
                       "show_camera","show_upload","show_voice","pending_input","input_submitted"]:
                st.session_state[k] = defaults[k]
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"Project context for '{selected_project_name}' loaded. How may I assist you, Architect?"
            })
            st.rerun()

        st.markdown("---")
        st.write(f"Project: **{st.session_state.selected_project or 'None'}**")
        st.write("Model: `gemini-2.5-flash`")
        st.write("Language: `Telugu (te-IN)`")
        st.write(f"GCP Project: `{GCP_PROJECT_ID}`")
        st.markdown("---")

        if st.button("Clear Chat History", key="clear_chat_button"):
            for k in ["messages","chat_history","uploaded_image_data","captured_image_data",
                       "uploaded_image_mime","has_image_input_this_turn","last_uploaded_bytes",
                       "last_camera_bytes","last_processed_audio","voice_text",
                       "show_camera","show_upload","show_voice","pending_input","input_submitted"]:
                st.session_state[k] = defaults[k]
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Chat history cleared. Awaiting your next directive, Architect."
            })
            st.rerun()

    # ── Chat Display ──
    st.markdown('<div class="chat-content-container">', unsafe_allow_html=True)
    for message in st.session_state.messages:
        role_class = "user-message-box" if message["role"] == "user" else ""
        with st.chat_message(message["role"]):
            if message.get("image_data") is not None:
                st.image(message["image_data"], caption="User Input Image", width=200)
            st.markdown(
                f"<div class='response-box {role_class}'>{message['content']}</div>",
                unsafe_allow_html=True
            )
            if message["role"] == "assistant" and "audio" in message:
                st.audio(message["audio"], format='audio/mp3')
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Status Chips ──
    chips = []
    if st.session_state.voice_text:          chips.append("🎙️ Voice ready")
    if st.session_state.uploaded_image_data: chips.append("🖼️ Image loaded")
    if st.session_state.captured_image_data: chips.append("📷 Photo captured")
    if chips:
        chip_html = " &nbsp; ".join(
            f"<span class='isira-status-chip'>{c}</span>" for c in chips
        )
        st.markdown(
            f"<div style='position:fixed;bottom:72px;left:5%;z-index:9998;"
            f"display:flex;gap:6px;align-items:center;'>{chip_html}</div>",
            unsafe_allow_html=True
        )

    # ── Handle query param actions (Safe execution block to avoid infinite loop) ──
    qp = st.query_params
    if "action" in qp:
        action_val = qp.get("action")
        msg_val = qp.get("msg", "") 
        st.query_params.clear() # Clear immediately to stop rerun recursion

        if action_val == "upload":
            st.session_state.show_upload = not st.session_state.show_upload
            st.session_state.show_camera = False
            st.session_state.show_voice = False
            st.rerun()
        elif action_val == "camera":
            st.session_state.show_camera = not st.session_state.show_camera
            st.session_state.show_upload = False
            st.session_state.show_voice = False
            st.rerun()
        elif action_val == "voice":
            st.session_state.show_voice = not st.session_state.show_voice
            st.session_state.show_upload = False
            st.session_state.show_camera = False
            st.rerun()
        elif action_val == "send":
            final_input_from_js = urllib.parse.unquote(msg_val).strip()
            if final_input_from_js or st.session_state.uploaded_image_data or st.session_state.captured_image_data:
                st.session_state.voice_text = ""
                _process_message(final_input_from_js)

    # ── Media Upload Panels ──
    if st.session_state.show_upload:
        with st.expander("📎 Upload Image", expanded=True):
            uploaded_file = st.file_uploader(
                "Choose Image",
                type=["jpg", "jpeg", "png", "webp"],
                key="image_uploader",
                label_visibility="collapsed"
            )
            if uploaded_file is not None:
                img_bytes = uploaded_file.read()
                if img_bytes != st.session_state.last_uploaded_bytes:
                    st.session_state.last_uploaded_bytes = img_bytes
                    st.session_state.uploaded_image_data = img_bytes
                    st.session_state.uploaded_image_mime = uploaded_file.type
                    st.session_state.has_image_input_this_turn = True
                    st.session_state.show_upload = False
                    st.rerun()

    if st.session_state.show_camera:
        with st.expander("📷 Camera", expanded=True):
            camera_photo = st.camera_input("Take Photo", key="camera_widget", label_visibility="collapsed")
            if camera_photo is not None:
                cam_bytes = camera_photo.read()
                if cam_bytes != st.session_state.last_camera_bytes:
                    st.session_state.last_camera_bytes = cam_bytes
                    st.session_state.captured_image_data = cam_bytes
                    st.session_state.uploaded_image_mime = "image/jpeg"
                    st.session_state.has_image_input_this_turn = True
                    st.session_state.show_camera = False
                    st.rerun()

    if st.session_state.show_voice:
        st.markdown("<p style='color:#00ffcc;font-size:0.8rem;margin-top:8px;'>🎙️ Voice Record చేయండి:</p>", unsafe_allow_html=True)
        audio_bytes = audio_recorder(
            text="",
            recording_color="#25D366",
            neutral_color="#00ffcc",
            icon_name="microphone",
            icon_size="lg",
            key="audio_recorder_widget"
        )
        if audio_bytes and len(audio_bytes) > 5000:
            if audio_bytes != st.session_state.last_processed_audio:
                st.session_state.last_processed_audio = audio_bytes
                with st.spinner("🎙️ Transcribing..."):
                    transcribed = transcribe_audio_gcp(audio_bytes)
                if transcribed and not transcribed.startswith("ERROR"):
                    st.session_state.voice_text = transcribed
                    st.session_state.show_voice = False
                    st.rerun()
                else:
                    st.warning("Audio processing failed.")

    # Image Previews
    if st.session_state.uploaded_image_data or st.session_state.captured_image_data:
        prev_col1, prev_col2, _ = st.columns([1, 1, 8])
        with prev_col1:
            if st.session_state.uploaded_image_data:
                st.image(st.session_state.uploaded_image_data, width=60, caption="Upload")
        with prev_col2:
            if st.session_state.captured_image_data:
                st.image(st.session_state.captured_image_data, width=60, caption="Camera")

    # ── HIDDEN native chat input ──
    voice_prefill = st.session_state.voice_text

    st.markdown("""
        <style>
        div[data-testid="stTextInput"]:has(input[aria-label="isira_hidden_input"]),
        div[data-testid="stTextInput"] { 
            position: absolute !important;
            top: -9999px !important;
            left: -9999px !important;
            width: 0 !important;
            height: 0 !important;
            overflow: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
        }
        </style>
    """, unsafe_allow_html=True)

    typed_val = st.text_input(
        "isira_hidden_input",
        value=voice_prefill,
        key="isira_text_input_field",
        label_visibility="collapsed"
    )

    # ── CUSTOM CHAT INPUT ROW ──
    components.html("""
    <script>
    (function() {{
        const parentDoc = window.parent.document;

        // ── Remove stale elements ──
        ['isira-popup-panel','isira-popup-style','isira-input-bar','isira-input-style'].forEach(id => {{
            const el = parentDoc.getElementById(id);
            if (el) el.remove();
        }});

        // ── Inject styles into parent ──
        const pStyle = parentDoc.createElement('style');
        pStyle.id = 'isira-input-style';
        pStyle.textContent = `
            #isira-input-bar {{
                position: fixed !important;
                bottom: 0 !important;
                left: 0 !important;
                width: 100% !important;
                z-index: 99998 !important;
                background: linear-gradient(to top, #000000 80%, transparent);
                padding: 10px 16px 14px 16px;
                display: flex;
                align-items: center;
                gap: 8px;
                box-sizing: border-box;
            }}
            #isira-plus-btn {{
                width: 42px; height: 42px;
                border-radius: 50%;
                background: rgba(0,255,204,0.15);
                border: 2px solid #00ffcc;
                color: #00ffcc;
                font-size: 1.6rem;
                cursor: pointer;
                display: flex; align-items: center; justify-content: center;
                flex-shrink: 0;
                transition: all 0.2s;
                font-weight: bold;
                line-height: 1;
            }}
            #isira-plus-btn:hover {{ background: #00ffcc; color: #000; }}
            #isira-text-input {{
                flex: 1;
                background: #000000;
                border: 2px solid #00ffcc;
                border-radius: 30px;
                color: #ffffff;
                padding: 10px 18px;
                font-size: 1rem;
                outline: none;
                caret-color: #00ffcc;
                box-shadow: 0 0 10px rgba(0,255,204,0.2);
                font-family: 'Space Grotesk', sans-serif;
            }}
            #isira-text-input::placeholder {{ color: rgba(255,255,255,0.35); }}
            #isira-send-btn {{
                width: 42px; height: 42px;
                border-radius: 50%;
                background: #00ffcc;
                border: none;
                color: #000;
                font-size: 1.2rem;
                cursor: pointer;
                display: flex; align-items: center; justify-content: center;
                flex-shrink: 0;
                transition: all 0.2s;
            }}
            #isira-send-btn:hover {{ background: #00e6b5; transform: scale(1.08); }}

            #isira-popup-panel {{
                position: fixed !important;
                bottom: 74px !important;
                left: 16px !important;
                z-index: 99999 !important;
                display: none;
                flex-direction: column;
                gap: 8px;
                background: rgba(0,12,12,0.98);
                border: 1.5px solid #00ffcc;
                border-radius: 16px;
                padding: 12px 10px;
                box-shadow: 0 0 28px rgba(0,255,204,0.45);
                min-width: 210px;
            }}
            #isira-popup-panel.pop-open {{ display: flex !important; }}
            .isira-pop-btn {{
                display: flex;
                align-items: center;
                gap: 10px;
                background: rgba(0,255,204,0.08);
                border: 1px solid rgba(0,255,204,0.35);
                border-radius: 10px;
                color: #00ffcc;
                padding: 10px 16px;
                font-size: 0.95rem;
                font-family: sans-serif;
                cursor: pointer;
                transition: all 0.18s;
                white-space: nowrap;
                width: 100%;
                text-align: left;
            }}
            .isira-pop-btn:hover {{ background: #00ffcc; color: #000; }}
        `;
        parentDoc.head.appendChild(pStyle);

        // ── Create input bar in parent body ──
        const bar = parentDoc.createElement('div');
        bar.id = 'isira-input-bar';
        bar.innerHTML = `
            <button id="isira-plus-btn" onclick="var p=window.parent.document.getElementById('isira-popup-panel'); if(p){{p.classList.toggle('pop-open');}}">+</button>
            <input id="isira-text-input" type="text" placeholder="Type a message..." value="${voice_prefill ? voice_prefill.replace(/"/g, '&quot;') : ''}" />
            <button id="isira-send-btn" onclick="window._isiraSend()">&#10148;</button>
        `;
        parentDoc.body.appendChild(bar);

        // ── Create popup panel in parent body ──
        const panel = parentDoc.createElement('div');
        panel.id = 'isira-popup-panel';
        panel.innerHTML = `
            <button class="isira-pop-btn" onclick="window._isiraAct('upload')">🖼️ &nbsp; Image Upload</button>
            <button class="isira-pop-btn" onclick="window._isiraAct('camera')">📷 &nbsp; Camera</button>
            <button class="isira-pop-btn" onclick="window._isiraAct('voice')">🎙️ &nbsp; Voice Input</button>
        `;
        parentDoc.body.appendChild(panel);

        // ── Enter key support ──
        const inp = parentDoc.getElementById('isira-text-input');
        inp.addEventListener('keydown', function(e) {{
            if (e.key === 'Enter') window._isiraSend();
        }});

        // ── Panel toggle ──
        let panelOpen = false;
        window._isiraTogglePanel = function() {{
            panelOpen = !panelOpen;
            panel.classList.toggle('pop-open', panelOpen);
        }};

        // Close panel on outside click
        parentDoc.addEventListener('click', function(e) {{
            if (!panelOpen) return;
            const plusBtn = parentDoc.getElementById('isira-plus-btn');
            if (!panel.contains(e.target) && e.target !== plusBtn) {{
                panelOpen = false;
                panel.classList.remove('pop-open');
            }}
        }});

        // ── Send ──
        window._isiraSend = function() {{
            const val = (parentDoc.getElementById('isira-text-input').value || '').trim();
            const url = new URL(window.parent.location.href);
            url.searchParams.set('action', 'send');
            url.searchParams.set('msg', encodeURIComponent(val));
            window.parent.location.href = url.toString();
        }};

        // ── Actions ──
        window._isiraAct = function(action) {{
            panelOpen = false;
            panel.classList.remove('pop-open');
            const url = new URL(window.parent.location.href);
            url.searchParams.set('action', action);
            window.parent.location.href = url.toString();
        }};

    }})();
    </script>
""", height=0)

    # ── Fallback check for image processing when text input is empty but image exists ──
    if st.session_state.has_image_input_this_turn and not qp.get("action"):
        st.session_state.has_image_input_this_turn = False
        _process_message("")

def _process_message(final_input: str):
    """Core Generative Model Engine — processes text + optional image."""
    active_image_data = st.session_state.captured_image_data or st.session_state.uploaded_image_data
    active_image_mime = st.session_state.uploaded_image_mime or "image/jpeg"
    has_image = active_image_data is not None

    if not final_input and not has_image:
        return

    display_text = final_input if final_input else "[Image shared for analysis]"

    st.session_state.messages.append({
        "role": "user",
        "content": display_text,
        "image_data": active_image_data if has_image else None,
    })

    current_turn_parts = []
    if has_image:
        current_turn_parts.append(
            Part.from_bytes(data=active_image_data, mime_type=active_image_mime)
        )
    if final_input:
        current_turn_parts.append(final_input)

    st.session_state.chat_history.append({"role": "user", "parts": current_turn_parts})

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
            st.session_state.chat_history.append(
                {"role": "model", "parts": [isira_response]}
            )

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

            # Resetting component specific flags safely
            st.session_state.show_plus_panel = False
            st.session_state.show_upload = False
            st.session_state.show_camera = False
            st.session_state.show_voice = False

        except Exception as e:
            err_msg = f"ISIRA Engine Error: {e}"
            logging.error(err_msg)
            st.error(err_msg)
            st.session_state.messages.append({"role": "assistant", "content": err_msg})

    st.session_state.uploaded_image_data = None
    st.session_state.captured_image_data = None
    st.session_state.uploaded_image_mime = None
    st.session_state.has_image_input_this_turn = False

    st.rerun()


st.markdown(
    "<p style='text-align:center;opacity:0.2;font-size:0.7rem;margin-top:40px;margin-bottom:120px; color:#ffffff !important;'>"
    "© 2026 DIGITAL DAARI // ARCHITECTURAL INTEGRITY VERIFIED</p>",
    unsafe_allow_html=True
)

# --- Entry Point ---
if __name__ == "__main__":
    if check_password():
        main_app()