"""
Voice Scheduling Agent - FastAPI Backend
Handles Vapi webhooks and creates Google Calendar events
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import uvicorn
import os

from routes import webhook, calendar

# Load environment variables from .env file
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    print("🚀 Starting Voice Scheduling Agent...")
    yield
    print("🛑 Shutting down...")


app = FastAPI(
    title="Voice Scheduling Agent",
    description="Real-time voice assistant for calendar scheduling",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(webhook.router, prefix="/webhook", tags=["webhooks"])
app.include_router(calendar.router, prefix="/calendar", tags=["calendar"])


@app.get("/")
async def root():
    return {
        "message": "Voice Scheduling Agent API",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/demo", response_class=HTMLResponse)
async def demo_page():
    public_key = os.getenv("VAPI_PUBLIC_KEY")
    assistant_id = os.getenv("VAPI_ASSISTANT_ID")

    if not public_key or not assistant_id:
        raise HTTPException(
            status_code=500,
            detail="Missing env vars. Set VAPI_PUBLIC_KEY and VAPI_ASSISTANT_ID to enable /demo.",
        )

    html = """<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Voice Scheduling Agent Demo</title>
    <style>
      body {{ font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; max-width: 760px; margin: 48px auto; padding: 0 16px; }}
      h1 {{ margin: 0 0 12px; }}
      p {{ color: #374151; line-height: 1.55; }}
      .row {{ display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }}
      button {{ background: #111827; color: white; border: 0; padding: 12px 16px; border-radius: 10px; cursor: pointer; font-size: 16px; }}
      button.secondary {{ background: #374151; }}
      button:disabled {{ opacity: .6; cursor: not-allowed; }}
      .box {{ border: 1px solid #e5e7eb; border-radius: 14px; padding: 16px; margin-top: 16px; }}
      .status {{ margin-top: 12px; padding: 12px 14px; border-radius: 12px; border: 1px solid #e5e7eb; background: #f9fafb; color: #111827; }}
      .success {{ border-color: #bbf7d0; background: #f0fdf4; }}
      .error {{ border-color: #fecaca; background: #fef2f2; }}
      .muted {{ color: #6b7280; }}
      code {{ background: #f3f4f6; padding: 2px 6px; border-radius: 6px; }}
    </style>
  </head>
  <body>
    <h1>Voice Scheduling Agent</h1>
    <p>Click <b>Start Call</b>, allow microphone access, and speak naturally.</p>
    <div class=\"row\">
      <button id=\"startBtn\">Start Call</button>
      <button id=\"stopBtn\" class=\"secondary\" disabled>End Call</button>
      <span id=\"callState\" class=\"muted\">Not started</span>
    </div>
    <div id=\"status\" class=\"status\">Ready.</div>

    <div class=\"box\">
      <p><b>Try saying</b></p>
      <p><code>Schedule a meeting tomorrow at 4pm</code></p>
    </div>

    <script>
      window.addEventListener('error', (e) => {
        const el = document.getElementById('status');
        if (el) {
          el.textContent = 'JS error: ' + (e?.message || 'unknown');
          el.className = 'status error';
        }
      });
      window.addEventListener('unhandledrejection', (e) => {
        const el = document.getElementById('status');
        if (el) {
          el.textContent = 'Promise error: ' + (e?.reason?.message || String(e?.reason || 'unknown'));
          el.className = 'status error';
        }
      });
    </script>

    <script type=\"module\">
      import Vapi from 'https://esm.sh/@vapi-ai/web';

      const publicKey = "__VAPI_PUBLIC_KEY__";
      const assistantId = "__VAPI_ASSISTANT_ID__";

      const startBtn = document.getElementById('startBtn');
      const stopBtn = document.getElementById('stopBtn');
      const callState = document.getElementById('callState');
      const statusEl = document.getElementById('status');

      const vapi = new Vapi(publicKey);

      const setStatus = (text, kind) => {
        statusEl.textContent = text;
        statusEl.className = 'status' + (kind ? ' ' + kind : '');
      };

      const setButtons = (inCall) => {
        startBtn.disabled = inCall;
        stopBtn.disabled = !inCall;
      };

      if (!window.isSecureContext && window.location.hostname !== 'localhost') {
        setStatus('This page is not in a secure context. Open via HTTPS (ngrok https) or use http://localhost.', 'error');
      }

      startBtn.addEventListener('click', async () => {
        setStatus('Starting call... please allow microphone access.', '');
        callState.textContent = 'Connecting...';
        try {
          await vapi.start(assistantId);
        } catch (e) {
          setStatus('Failed to start call: ' + (e?.message || String(e)), 'error');
          callState.textContent = 'Error';
          setButtons(false);
        }
      });

      stopBtn.addEventListener('click', () => {
        setStatus('Ending call...', '');
        vapi.stop();
      });

      vapi.on('call-start', () => {
        setButtons(true);
        callState.textContent = 'In call';
        setStatus('Call started. Speak now.', '');
      });

      vapi.on('call-end', () => {
        setButtons(false);
        callState.textContent = 'Ended';
        if (statusEl.textContent === 'Ending call...') {
          setStatus('Call ended.', '');
        }
      });

      vapi.on('message', (message) => {
        try {
          // Primary: server tool finished
          if (message?.type === 'tool-calls-result') {
            const results = message.results || message.toolCallResults || [];
            const anySuccess = Array.isArray(results) && results.some(r => {
              const res = r?.result || r;
              return (
                res?.success === true ||
                res?.status === 'success' ||
                Boolean(res?.htmlLink) ||
                Boolean(res?.eventId)
              );
            });

            if (anySuccess) {
              setStatus('Meeting created successfully. Ending call...', 'success');
              setTimeout(() => vapi.stop(), 1200);
              return;
            }
          }

          // Fallback: rely on assistant's spoken confirmation (do not display transcript)
          if (message?.type === 'transcript' && message.role === 'assistant') {
            const t = String(message.transcript || '').toLowerCase();
            if (
              t.includes('scheduled') ||
              t.includes('has been scheduled') ||
              t.includes('has been booked')
            ) {
              setStatus('Meeting created successfully. Ending call...', 'success');
              setTimeout(() => vapi.stop(), 1200);
              return;
            }
          }
        } catch (e) {
          // ignore UI errors
        }
      });
    </script>
  </body>
</html>"""

    html = html.replace("__VAPI_PUBLIC_KEY__", public_key).replace("__VAPI_ASSISTANT_ID__", assistant_id)
    return html


@app.get("/start-call")
async def start_call():
    return RedirectResponse(url="/demo", status_code=302)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
