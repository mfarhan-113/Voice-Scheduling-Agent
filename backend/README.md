# Voice Scheduling Agent

Real-time voice assistant that creates Google Calendar events through natural conversation.

## Deployed URL
**Coming soon** - Deployed link will be added here

## How It Works

1. **User** opens Vapi hosted assistant link and speaks
2. **Vapi** handles voice → text → voice with GPT-4o
3. **Backend** (this FastAPI app) receives tool calls via webhooks
4. **Google Calendar** API creates the event
5. **User** receives confirmation with calendar link

## Quick Start (Local Development)

### 1. Prerequisites
- Python 3.10+
- Google Account
- Vapi Account (free)

### 2. Setup

```bash
# Navigate to backend folder
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
copy .env.example .env
```

### 3. Get Google Calendar API Credentials

**Step-by-step:**

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project → Name it "Voice Calendar Agent"
3. **Enable APIs**: 
   - Go to "APIs & Services" → "Library"
   - Search "Google Calendar API" → Click "Enable"
4. **Create OAuth Credentials**:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth 2.0 Client ID"
   - Select "Web application"
   - Name: "Voice Calendar Agent"
   - **Authorized redirect URIs**: Add `http://localhost:8000/calendar/auth/google/callback`
   - Click "Create"
5. **Copy credentials**:
   - You'll see a popup with Client ID and Client Secret
   - Copy these to your `.env` file:
     ```
     GOOGLE_CLIENT_ID=your_client_id_here
     GOOGLE_CLIENT_SECRET=your_client_secret_here
     ```

### 4. Get Refresh Token (One-time setup)

```bash
# Start the server
python main.py

# In browser, visit:
http://localhost:8000/calendar/auth/google
```

- Sign in with the Google account whose calendar you want to use
- Grant permissions
- Copy the `refresh_token` from the response
- Paste it in your `.env` file:
  ```
  GOOGLE_REFRESH_TOKEN=your_refresh_token_here
  ```

### 5. Test Calendar Connection

```bash
# Restart server
python main.py

# Test in browser:
http://localhost:8000/calendar/test
```

Should return: `{"status": "success", "calendars_found": X}`

### 6. Start Server

```bash
python main.py
```

Server runs at `http://localhost:8000`

### 7. Configure Vapi Assistant

1. Go to [Vapi Dashboard](https://dashboard.vapi.ai)
2. Create new Assistant
3. **System Prompt** (copy-paste):

```
You are a helpful scheduling assistant. Your goal is to create calendar events for users.

Follow this conversation flow:

1. GREETING: "Hi! I'm your scheduling assistant. I can create a calendar event for you. What's your name?"

2. COLLECT NAME: Wait for user's name, acknowledge it.

3. COLLECT DATETIME: Ask "Hi [name]! What date and time should I schedule the meeting for?"
   - Accept natural language like "tomorrow at 3pm", "next Tuesday at 10am", "March 15th 2:30 PM"

4. CLARIFY TIMEZONE (if needed): Ask "Which timezone should I use?" if not clear.
   - Common options: Pakistan Time (PKT), India Time (IST), Eastern Time (EST), Pacific Time (PST), UTC

5. COLLECT TITLE (optional): "Would you like to give this meeting a title? (say 'skip' to use default)"
   - Default: "Meeting with [name]"

6. CONFIRMATION: Read back all details:
   - "Let me confirm: Meeting titled '[title]' on [date] at [time] [timezone] for 30 minutes. Should I create this event?"

7. CREATE EVENT: When user confirms (says "yes", "sure", "create it"), call the create_calendar_event function with:
   - title: meeting title
   - start_datetime: ISO format datetime
   - duration_minutes: 30 (default)
   - timezone: IANA timezone
   - description: "Scheduled by Voice Assistant"

8. SUCCESS: When function returns, say:
   "Perfect! I've created your event. Here's the link: [htmlLink]. The meeting is scheduled for [date] at [time]. Is there anything else I can help with?"

Important notes:
- Always confirm details before creating the event
- Parse natural language dates to ISO format
- Be friendly and conversational
- If user wants to change something, go back to the relevant step
```

4. **Add Tool** (create_calendar_event):
   - Go to "Tools" tab
   - Click "Add Function"
   - Name: `create_calendar_event`
   - Description: "Create a Google Calendar event with the specified details"
   - Parameters:
   ```json
   {
     "type": "object",
     "properties": {
       "title": {
         "type": "string",
         "description": "The title of the meeting"
       },
       "start_datetime": {
         "type": "string",
         "description": "Start time in ISO 8601 format (e.g., 2026-02-27T15:00:00+05:00)"
       },
       "duration_minutes": {
         "type": "integer",
         "description": "Duration of the meeting in minutes",
         "default": 30
       },
       "timezone": {
         "type": "string",
         "description": "IANA timezone name (e.g., Asia/Karachi, America/New_York)",
         "default": "UTC"
       },
       "description": {
         "type": "string",
         "description": "Optional description for the event"
       }
     },
     "required": ["title", "start_datetime"]
   }
   ```
   - **Webhook URL**: `http://localhost:8000/webhook/vapi`

5. **Get Assistant Link**:
   - In Vapi dashboard, find "Assistant Link" or "Share"
   - Copy the public URL - this is what users will open to talk to the agent

### 8. Test the Full Flow

1. Open Vapi assistant link in browser
2. Allow microphone access
3. Have a conversation:
   - "Hi, I'm John"
   - "Schedule for tomorrow at 3pm"
   - "Pakistan time"
   - "Project Kickoff"
   - "Yes, create it"
4. Check your Google Calendar - event should appear!

## Deployment (Render)

### 1. Push to GitHub (optional)
```bash
git init
git add .
git commit -m "Initial commit"
git push origin main
```

### 2. Deploy to Render
1. Go to [Render](https://dashboard.render.com)
2. Click "New" → "Web Service"
3. Connect your GitHub repo or use "Deploy from Git URL"
4. Configure:
   - **Name**: voice-calendar-agent
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
5. **Environment Variables**: Add all from `.env`
6. Click "Create Web Service"

### 3. Update Vapi Webhook URL
- In Vapi dashboard, change webhook URL from localhost to your Render URL:
  `https://your-app-name.onrender.com/webhook/vapi`

### 4. Update Google OAuth Redirect URI
- In Google Cloud Console, add your Render URL:
  `https://your-app-name.onrender.com/calendar/auth/google/callback`

## Calendar Integration Explained

### Authentication Flow
We use **OAuth 2.0 with Refresh Token**:

1. **Initial Setup**: User authorizes app once via OAuth flow
2. **Refresh Token**: Stored in environment variable, never expires
3. **API Calls**: Backend uses refresh token to get temporary access token
4. **Event Creation**: Creates events in user's primary calendar

### Why This Approach?
- **Secure**: No storing passwords
- **Persistent**: Works continuously without re-login
- **Standard**: Industry-standard for Google API access
- **Scoped**: Only requests calendar permissions, nothing else

### Data Flow
```
User speaks to Vapi
    ↓
Vapi sends webhook to our FastAPI backend
    ↓
Backend validates request
    ↓
Backend calls Google Calendar API (authenticated)
    ↓
Event created in user's Google Calendar
    ↓
Success response sent back to Vapi
    ↓
Vapi speaks confirmation to user
```

## Project Structure

```
backend/
├── main.py                 # FastAPI entry point
├── routes/
│   ├── webhook.py          # Vapi webhook handlers
│   └── calendar.py         # Google Calendar OAuth routes
├── services/
│   └── calendar_service.py # Google Calendar API integration
├── utils/
│   └── date_helpers.py     # Natural language date parsing
├── requirements.txt        # Python dependencies
├── .env.example           # Environment template
└── README.md              # This file
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/health` | GET | Detailed health status |
| `/webhook/vapi` | POST | Vapi tool call webhook |
| `/webhook/test` | GET | Test webhook endpoint |
| `/calendar/auth/google` | GET | Start OAuth flow |
| `/calendar/auth/google/callback` | GET | OAuth callback |
| `/calendar/test` | GET | Test calendar connection |
| `/docs` | GET | Swagger API documentation |

## Troubleshooting

### "GOOGLE_REFRESH_TOKEN not set"
- Run OAuth flow: `http://localhost:8000/calendar/auth/google`
- Copy refresh token to `.env`

### "Invalid client" error
- Check GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in `.env`
- Ensure no extra spaces or quotes

### Vapi webhook not working
- Check BASE_URL in `.env` matches your actual server URL
- Ensure server is accessible (not behind firewall)
- Check `/webhook/test` endpoint responds

### Calendar event not created
- Check `/calendar/test` works first
- Review server logs for error messages
- Verify refresh token is valid (re-run OAuth if needed)

## Screenshots / Proof

**Will be added after deployment**:
- [ ] Vapi assistant conversation screenshot
- [ ] Google Calendar event created screenshot
- [ ] Terminal logs showing successful webhook call

## License

MIT
