"""
Google Calendar OAuth Routes
Used to get the initial refresh token
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
import os
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
import json

router = APIRouter()

# OAuth configuration
SCOPES = ['https://www.googleapis.com/auth/calendar']


def get_client_config():
    """Get OAuth client configuration from environment"""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/calendar/auth/google")
    
    if not client_id or not client_secret:
        raise ValueError("Google OAuth credentials not configured")
    
    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri]
        }
    }, redirect_uri


CLIENT_SECRETS_FILE = os.getenv("GOOGLE_CLIENT_SECRETS_FILE", "client_secret.json")


@router.get("/auth/google")
async def google_auth_handler(request: Request, code: str = None, state: str = None, error: str = None):
    """
    Handle both OAuth initiation and callback at the same endpoint
    """
    # If we have a code, this is the callback
    if code:
        return await handle_callback(code, error)
    
    # Otherwise, initiate OAuth flow
    return await initiate_oauth()


async def initiate_oauth():
    """Start OAuth flow - redirect to Google"""
    try:
        client_config, redirect_uri = get_client_config()
        
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'  # Force to get refresh token
        )
        
        return RedirectResponse(url=authorization_url)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth initiation failed: {str(e)}")


async def handle_callback(code: str, error: str = None):
    """Handle OAuth callback - exchange code for tokens"""
    if error:
        return JSONResponse(
            status_code=400,
            content={"error": error, "message": "Authorization was denied"}
        )
    
    if not code:
        return JSONResponse(
            status_code=400,
            content={"error": "missing_code", "message": "No authorization code received"}
        )
    
    try:
        client_config, redirect_uri = get_client_config()
        
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
        
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        if not credentials.refresh_token:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "no_refresh_token",
                    "message": "No refresh token received. You may have already authorized this app before.",
                    "solution": "Go to https://myaccount.google.com/permissions and revoke access, then try again."
                }
            )
        
        # Return the refresh token (SAVE THIS!)
        response_data = {
            "message": "Authorization successful! Copy the refresh_token below to your .env file",
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "scopes": credentials.scopes,
            "instructions": [
                "1. Copy the refresh_token above",
                "2. Add it to your .env file as: GOOGLE_REFRESH_TOKEN=<token>",
                "3. The app can now create calendar events without re-authorizing",
                "4. Restart the server"
            ]
        }
        
        print("✅ Google OAuth successful! Refresh token obtained.")
        print(f"Token: {credentials.refresh_token}")
        return JSONResponse(content=response_data)
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": "token_exchange_failed", "message": str(e)}
        )


@router.get("/auth/google/callback")
async def google_auth_callback_legacy(request: Request, code: str = None, error: str = None):
    """
    Legacy callback endpoint - redirects to main handler
    """
    return await handle_callback(code, error)


@router.get("/test")
async def test_calendar_connection():
    """Test if calendar connection is working"""
    from services.calendar_service import get_calendar_service
    
    try:
        service = get_calendar_service()
        # Try to list calendars
        calendars = service.calendarList().list().execute()
        return {
            "status": "success",
            "message": "Connected to Google Calendar",
            "calendars_found": len(calendars.get('items', []))
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to connect: {str(e)}",
            "hint": "Make sure GOOGLE_REFRESH_TOKEN is set in .env"
        }
