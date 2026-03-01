"""
Date and Time Parsing Utilities
Handles natural language date/time parsing
"""
from datetime import datetime, timedelta
from typing import Dict, Optional
import pytz
import dateparser
from dateutil import parser as dateutil_parser


def parse_natural_datetime(text: str, timezone: str = "UTC", base_time: Optional[datetime] = None) -> Dict:
    """
    Parse natural language datetime expressions
    
    Examples:
        - "tomorrow at 3pm"
        - "next Tuesday at 10am"
        - "March 15th, 2:30 PM"
        - "in 2 hours"
        - "Friday at 5pm"
    
    Args:
        text: Natural language datetime string
        timezone: Target timezone (IANA format, e.g., 'Asia/Karachi')
        base_time: Reference time for relative parsing (default: now)
    
    Returns:
        Dict with parsed datetime info
    """
    if base_time is None:
        base_time = datetime.now(pytz.timezone(timezone))
    
    # Configure dateparser with timezone
    settings = {
        'RELATIVE_BASE': base_time.replace(tzinfo=None),
        'TIMEZONE': timezone,
        'RETURN_AS_TIMEZONE_AWARE': True,
        'PREFER_DATES_FROM': 'future',
        'PREFER_DAY_OF_MONTH': 'current',
    }
    
    # Try dateparser first (good for relative dates)
    parsed = dateparser.parse(text, settings=settings)
    
    # If dateparser fails, try dateutil
    if parsed is None:
        try:
            parsed = dateutil_parser.parse(text, fuzzy=True)
            # Make timezone aware
            if parsed.tzinfo is None:
                tz = pytz.timezone(timezone)
                parsed = tz.localize(parsed)
        except (ValueError, TypeError):
            parsed = None
    
    if parsed is None:
        return {
            "success": False,
            "error": f"Could not parse: '{text}'",
            "startIso": None,
            "endIso": None,
            "timezone": timezone,
            "confidence": "low",
            "needsClarification": True
        }
    
    # Ensure timezone is correct
    tz = pytz.timezone(timezone)
    if parsed.tzinfo is None:
        parsed = tz.localize(parsed)
    else:
        parsed = parsed.astimezone(tz)
    
    # Default duration is 30 minutes
    end_time = parsed + timedelta(minutes=30)
    
    # Format as ISO strings
    start_iso = parsed.isoformat()
    end_iso = end_iso = end_time.isoformat()
    
    # Determine confidence based on parsing quality
    confidence = "high"
    needs_clarification = False
    
    # Check for ambiguous cases
    text_lower = text.lower()
    ambiguous_keywords = ['soon', 'later', 'sometime', 'whenever', 'maybe']
    if any(kw in text_lower for kw in ambiguous_keywords):
        confidence = "low"
        needs_clarification = True
    
    # Check if year was specified (if not, might be ambiguous)
    if str(datetime.now().year) not in text and str(datetime.now().year + 1) not in text:
        # If date is more than 1 year in future, might have been misinterpreted
        if (parsed - datetime.now(pytz.timezone(timezone))).days > 365:
            confidence = "medium"
    
    return {
        "success": True,
        "startIso": start_iso,
        "endIso": end_iso,
        "timezone": timezone,
        "confidence": confidence,
        "needsClarification": needs_clarification,
        "originalText": text
    }


def format_datetime_for_display(iso_string: str, timezone: str = "UTC") -> str:
    """
    Format ISO datetime for human-readable display
    
    Example: 2026-02-27T15:00:00+05:00 → "February 27, 2026 at 3:00 PM"
    """
    try:
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        tz = pytz.timezone(timezone)
        dt = dt.astimezone(tz)
        return dt.strftime("%B %d, %Y at %I:%M %p")
    except Exception as e:
        return iso_string


def get_common_timezones() -> list:
    """Return list of common timezones for user selection"""
    return [
        "UTC",
        "Asia/Karachi",        # Pakistan
        "Asia/Dubai",          # UAE
        "Asia/Kolkata",        # India
        "Europe/London",       # UK
        "Europe/Paris",        # Central Europe
        "America/New_York",    # US Eastern
        "America/Chicago",     # US Central
        "America/Denver",      # US Mountain
        "America/Los_Angeles", # US Pacific
        "Asia/Tokyo",          # Japan
        "Australia/Sydney",    # Australia
    ]
