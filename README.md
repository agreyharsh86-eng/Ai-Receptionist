# 🏢 Apex Horizon Enterprises — Corporate AI Voice Receptionist

An enterprise-grade, real-time Voice AI Receptionist and Front Desk Concierge system powered by **Google Gemini 3.1 Flash Live** (bidirectional low-latency audio streaming) and **FastAPI**.

Designed for corporate front desks to greet callers and visitors, query corporate policies and office directions, inspect staff availability, book and cancel calendar appointments, take detailed caller messages, and route calls.

---

## ✨ Features

- **🎙️ Real-Time Voice Conversations**: Low-latency bidirectional audio streaming using Google Gemini 3.1 Flash Live (`gemini-3.1-flash-live-preview`).
- **🌊 Dynamic Audio Visualizer**: Real-time waveform canvas reacting to user speech and receptionist voice playback.
- **⚡ Synchronous Tool Execution**: The receptionist natively calls functions in real time:
  - `check_availability`: Checks open calendar slots for staff members or departments.
  - `book_appointment`: Schedules appointments with instant SQLite database sync.
  - `cancel_appointment`: Cancels scheduled appointments.
  - `leave_message`: Takes caller voicemails and messages when staff are busy or out of office.
  - `lookup_directory`: Searches employee extensions, job titles, and live office presence status.
  - `get_company_info`: Answers questions regarding office hours, parking, Wi-Fi, visitor security badges, and dining amenities.
  - `transfer_call`: Simulates routing callers to extensions or departments.
- **📅 Interactive Front-Desk Management Console**:
  - **Appointments Hub**: Real-time list of booked visitors with instant live updates when the AI schedules a meeting.
  - **Caller Messages Inbox**: Centralized message log with urgency tags (Urgent/Normal) and read tracking.
  - **Corporate Staff Directory**: Searchable directory with live availability badges.
  - **Company FAQs & Facility Guidelines**: Pre-loaded corporate knowledge base.
  - **Call History**: Recorded sessions, duration, and transcripts.
- **💬 Text & Speech Fallback Mode**: Type directly in the console or use browser speech synthesis if a microphone is not connected.
- **⚙️ Settings Drawer**: Configure your Gemini API key, select voice persona (`Aoede`, `Puck`, `Charon`, `Fenrir`, `Kore`), and manage connections.

---

## 🛠️ Architecture

```
Ai Receptionist/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI initialization & static mount
│   ├── config.py                # Environment & business configurations
│   ├── database.py              # SQLite schema, tables & seed data
│   ├── tools/
│   │   └── receptionist_tools.py # Executable Gemini tools & DB queries
│   ├── services/
│   │   └── gemini_live.py       # Live WebSocket bridge with Google GenAI
│   └── api/
│       ├── routes.py            # REST API endpoints (company, appts, msgs)
│       └── websocket.py         # WebSocket /ws/live endpoint
├── static/
│   ├── index.html               # Luxury executive console UI
│   ├── css/
│   │   └── styles.css           # Glassmorphic dark executive design system
│   └── js/
│       ├── audio-player.js      # 24kHz PCM gapless audio streamer
│       ├── audio-processor.js   # 16kHz PCM microphone capturer
│       └── app.js               # Frontend controller & visualizer
├── tests/
│   └── test_backend.py          # Unit & integration test suite
├── run.py                       # One-command server launcher
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment template
└── README.md
```

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.11)
- Google Gemini API Key ([Get one at Google AI Studio](https://aistudio.google.com/))

### 2. Setup & Installation

Clone or open the directory in terminal:
```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure API Key
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```
*(Alternatively, you can launch the app and enter your API key directly in the web UI Settings drawer.)*

### 4. Run the Application
Launch the server with:
```powershell
.venv\Scripts\python run.py
```

Open your browser and navigate to:
```
http://127.0.0.1:8000
```

---

## 🧪 Running Tests

To verify the database, tools, and REST API endpoints:
```powershell
.venv\Scripts\python -m unittest tests/test_backend.py
```
All tests execute against SQLite and verify availability checks, bookings, cancellations, directory lookups, and message logging.

---

## 🎙️ How to Interact with Aria (Receptionist)

Click **"Start Voice Call"** and speak naturally with Aria:
1. **Corporate Information**:
   - *"What are your office hours and where are you located?"*
   - *"Where can visitors park, and what is the Wi-Fi password?"*
2. **Scheduling a Meeting**:
   - *"I need to book a meeting with Marcus Sterling in Enterprise Sales tomorrow at 2 PM."*
   - The AI checks calendar availability, prompts for your details, confirms the booking, and the appointment instantly appears in your **Appointments** tab!
3. **Staff Lookup & Messages**:
   - *"Is Sarah Jenkins available to speak?"*
   - Receptionist checks directory, notices Sarah is *"In Client Call"*, and offers to take a message.
   - *"Please tell her David called about the cloud security audit report."*
   - The message is logged and immediately visible in the **Caller Messages** tab!
