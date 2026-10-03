ISIRA Master Engine

Multimodal Generative AI Assistant

ISIRA Master Engine is an AI-powered multimodal assistant built with Python, Streamlit, Google Cloud Vertex AI, and Gemini.

The project combines conversational AI, image understanding, Telugu voice interaction, speech recognition, text-to-speech, Google Sheets integration, and a custom interactive UI into a single AI application.

---

🚀 Key Features

- 🤖 Generative AI powered by Gemini through Google Cloud Vertex AI
- 🖼️ Multimodal image interaction with image upload and AI analysis
- 🎤 Voice input using Google Cloud Speech-to-Text
- 🗣️ Telugu language support for natural voice interaction
- 🔊 Text-to-Speech using Google Cloud Text-to-Speech
- 🎧 Audio normalization using FFmpeg for reliable speech recognition
- 📊 Google Sheets integration for project context and lead storage
- 🔐 Secure configuration using Streamlit Secrets
- 💬 Interactive Streamlit chat interface
- ⚡ Session state, caching and error handling
- 🎨 Custom HTML, CSS and JavaScript interface
- 🌐 Three.js animated visual interface
- ☁️ Google Cloud integration for scalable AI services

---

🧠 AI Architecture

ISIRA is designed as a modular AI application with multiple services working together:

                    ┌──────────────────────┐
                    │      User Input      │
                    │ Text / Voice / Image │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Streamlit UI Layer  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │    ISIRA AI Engine   │
                    │ Gemini / Vertex AI   │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
       Speech-to-Text     Image Analysis   Google Sheets
              │                │                │
              └────────────────┼────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │    AI Response       │
                    └──────────┬───────────┘
                               │
                    ┌──────────┴───────────┐
                    ▼                      ▼
              Text Response          Text-to-Speech

---

🛠️ Technology Stack

AI & Cloud

- Google Cloud Vertex AI
- Gemini
- Google Cloud Speech-to-Text
- Google Cloud Text-to-Speech
- Google Sheets API

Backend & Application

- Python
- FastAPI
- Uvicorn
- Streamlit

Frontend

- HTML
- CSS
- JavaScript
- Three.js

Audio Processing

- FFmpeg
- WAV / PCM audio processing
- Audio format normalization

---

📁 Project Structure

ISIRA-Master-Engine/
│
├── app.py
├── app_ui.py
├── requirements.txt
├── Dockerfile
├── isira_setup.py
│
├── backend/
│   └── app/
│       ├── speech_service.py
│       └── ...
│
├── isira-v1.2.6/
│   └── core/
│       └── ...
│
├── .gitignore
├── .gcloudignore
└── README.md

---

🎤 Voice Processing Pipeline

ISIRA supports voice interaction through Google Cloud Speech-to-Text.

The application can normalize incoming audio using FFmpeg before sending it to Google Speech-to-Text.

Audio Input
     │
     ▼
FFmpeg Conversion
     │
     ▼
16 kHz Mono PCM WAV
     │
     ▼
Google Speech-to-Text
     │
     ▼
Telugu / English Transcript
     │
     ▼
ISIRA AI

This approach improves compatibility with different audio formats such as M4A/AAC, WAV and WebM/Opus.

---

🔐 Security

Sensitive credentials are intentionally excluded from the repository.

ISIRA uses secure configuration for:

- Google Cloud credentials
- Vertex AI configuration
- Authentication settings
- Google Sheets configuration
- Application secrets

Important

Never commit the following to GitHub:

- Service account JSON files
- API keys
- Passwords
- Access tokens
- ".streamlit/secrets.toml"
- ".env" files

Sensitive runtime files are excluded through ".gitignore".

---

⚙️ Installation

Clone the repository and create a Python virtual environment.

git clone <repository-url>
cd ISIRA-Master-Engine

Create and activate a virtual environment:

python3 -m venv venv
source venv/bin/activate

Install dependencies:

pip install -r requirements.txt

Make sure FFmpeg is installed on the system for audio processing.

---

▶️ Running the Application

Start the Streamlit application:

streamlit run app_ui.py

If the backend service is required, start the FastAPI application with:

uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

---

☁️ Google Cloud

ISIRA is designed to work with Google Cloud services including:

- Vertex AI
- Gemini
- Speech-to-Text
- Text-to-Speech
- Google Sheets API

Cloud credentials and configuration should be provided through secure runtime configuration rather than hard-coded into the source code.

---

🌍 Language Support

The voice architecture is designed with Indian language interaction in mind.

Supported speech languages include:

- Telugu
- English
- Hindi
- Tamil
- Kannada
- Malayalam
- Marathi
- Bengali
- Gujarati
- Punjabi
- Urdu

---

🎯 Project Goals

The goal of ISIRA Master Engine is to build a powerful, scalable and multimodal AI assistant capable of combining:

Text + Voice + Images + Generative AI + Cloud Services

into a unified application experience.

---

🔮 Future Improvements

Planned areas for further development include:

- Advanced multimodal reasoning
- Improved conversational memory
- More AI automation workflows
- Expanded language support
- Enhanced voice interaction
- Production-grade monitoring
- Cloud deployment optimization
- Advanced architectural intelligence
- Improved UI/UX
- Scalable AI service orchestration

---

👨‍💻 Developer

Guggilla Prashanth

AI Application Developer | Generative AI | Python | Google Cloud

Focus Areas

- Generative AI
- Google Cloud
- Python
- AI Application Development
- Multimodal AI
- Voice AI
- Cloud Architecture

---

⭐ Project

ISIRA Master Engine

A multimodal Generative AI application built with Python, Streamlit and Google Cloud.

If you find the project interesting, explore the repository and follow the development journey.

---

📜 License

This project is currently maintained as an independent AI application project.