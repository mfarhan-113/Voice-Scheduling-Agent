# Voice Scheduling Agent

Real-time voice scheduling assistant that creates Google Calendar events via natural conversation.

## Deployed URL

- **Backend**: https://voice-scheduling-agent-qn7g.onrender.com/
- **Public Demo (no Vapi account needed)**: https://voice-scheduling-agent-qn7g.onrender.com/demo

## How to Test the Agent (Deployed)

### Option A: Web Demo (recommended)

1. Open: https://voice-scheduling-agent-qn7g.onrender.com/demo
2. Click `Start Call`
3. Allow microphone access
4. Speak naturally, for example:
   - `Schedule a meeting tomorrow at 4pm`
   - `Schedule a meeting next Tuesday at 10am Pakistan time`
5. Confirm the details when the assistant asks.
6. After the meeting is created:
   - The page shows a success message
   - The call auto-ends
7. Verify the event in Google Calendar (connected account).

### Option B: API Health Checks

- `GET /health`: https://voice-scheduling-agent-qn7g.onrender.com/health
- `GET /docs`: https://voice-scheduling-agent-qn7g.onrender.com/docs

## (Optional) Run Locally

### Prerequisites

- Python 3.10+
- A Google Cloud project with Google Calendar API enabled
- A Vapi assistant (for `/demo`) and Vapi Web Public Key

### Setup

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
copy .env.example .env
```

Fill in `.env` values:

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REFRESH_TOKEN`
- `VAPI_PUBLIC_KEY`
- `VAPI_ASSISTANT_ID`

Run:

```bash
python main.py
```

Open:

- http://localhost:8000/demo

## Calendar Integration (Google Calendar)

### Auth model

This project uses **OAuth 2.0 + Refresh Token** (server-side):

- During a one-time authorization, you obtain a `refresh_token`.
- The backend stores it in an environment variable (`GOOGLE_REFRESH_TOKEN`).
- For each request, the backend exchanges refresh token → short-lived access token.
- The event is created in the user’s **primary** Google Calendar.

### Data flow

1. User speaks in the Vapi web call (`/demo`).
2. Vapi triggers a tool call to the backend webhook:
   - `POST /webhook/vapi`
3. Backend parses the requested date/time (supports natural language), then calls Google Calendar API.
4. Backend returns tool result to Vapi, and the assistant confirms success.

## Key Endpoints

- `GET /demo` - web-based voice call demo
- `POST /webhook/vapi` - Vapi tool-call webhook
- `GET /calendar/auth/google` - OAuth start (local / initial setup)
- `GET /calendar/test` - calendar connection test

