"""
Google Calendar Service
Handles authentication and event creation
"""
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta
from typing import Dict, Optional
import pytz


def get_calendar_service():
    """
    Get authenticated Google Calendar service using refresh token
    """
    # Load credentials from environment
    refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN")
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    
    if not refresh_token:
        raise ValueError("GOOGLE_REFRESH_TOKEN not set in environment variables")
    
    if not client_id or not client_secret:
        raise ValueError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set")
    
    # Create credentials from refresh token
    credentials = Credentials(
        token=None,  # No access token initially, will be refreshed
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=['https://www.googleapis.com/auth/calendar']
    )
    
    # Refresh the token to get a valid access token
    credentials.refresh(GoogleRequest())
    
    # Build the service
    service = build('calendar', 'v3', credentials=credentials)
    
    return service


def create_calendar_event(
    title: str,
    start_datetime: str,
    duration_minutes: int = 30,
    timezone: str = "UTC",
    description: str = "Scheduled by Voice Assistant",
    attendees: Optional[list] = None
) -> Dict:
    """
    Create a calendar event
    
    Args:
        title: Event title/summary
        start_datetime: ISO format datetime string
        duration_minutes: Meeting duration in minutes
        timezone: IANA timezone name (e.g., 'Asia/Karachi', 'America/New_York')
        description: Event description
        attendees: List of attendee emails (optional)
    
    Returns:
        Created event object from Google Calendar API
    """
    service = get_calendar_service()
    
    # Parse start time
    if isinstance(start_datetime, str):
        # Handle ISO format
        if 'Z' in start_datetime:
            start_datetime = start_datetime.replace('Z', '+00:00')
        start_time = datetime.fromisoformat(start_datetime)
    else:
        start_time = start_datetime
    
    # Ensure timezone is set
    tz = pytz.timezone(timezone)
    if start_time.tzinfo is None:
        start_time = tz.localize(start_time)
    
    # Calculate end time
    end_time = start_time + timedelta(minutes=duration_minutes)
    
    # Format times for Google Calendar API
    start_iso = start_time.isoformat()
    end_iso = end_time.isoformat()
    
    # Build event body
    event = {
        'summary': title,
        'description': description,
        'start': {
            'dateTime': start_iso,
            'timeZone': timezone,
        },
        'end': {
            'dateTime': end_iso,
            'timeZone': timezone,
        },
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 30},
                {'method': 'popup', 'minutes': 10},
            ],
        },
    }
    
    # Add attendees if provided
    if attendees:
        event['attendees'] = [{'email': email} for email in attendees]
    
    try:
        # Create the event
        created_event = service.events().insert(
            calendarId='primary',
            body=event,
            sendUpdates='all' if attendees else 'none'
        ).execute()
        
        print(f"✅ Event created: {created_event.get('htmlLink')}")
        return created_event
        
    except HttpError as e:
        print(f"❌ Google Calendar API error: {e}")
        raise


def list_upcoming_events(max_results: int = 10) -> list:
    """
    List upcoming events from primary calendar
    Useful for testing the connection
    """
    service = get_calendar_service()
    
    # Get current time in UTC
    now = datetime.utcnow().isoformat() + 'Z'
    
    try:
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        return events
        
    except HttpError as e:
        print(f"❌ Failed to list events: {e}")
        raise
