"""
Vapi Webhook Handlers
Handles tool calls from Vapi voice assistant
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
from services.calendar_service import create_calendar_event
from utils.date_helpers import parse_natural_datetime
import json
import re

router = APIRouter()


class VapiToolCall(BaseModel):
    """Vapi tool call request structure"""
    message: dict
    call: Optional[dict] = None


class CreateEventParams(BaseModel):
    """Parameters for create_calendar_event tool"""
    title: str
    start_datetime: str  # ISO format or natural language
    duration_minutes: int = 30
    description: Optional[str] = None
    timezone: Optional[str] = "UTC"


@router.post("/vapi")
async def handle_vapi_webhook(request: Request):
    """
    Main webhook endpoint for Vapi tool calls
    Vapi sends tool call requests here when user confirms details
    """
    try:
        raw_body = await request.body()
        if not raw_body:
            return {
                "results": [
                    {"toolCallId": "unknown", "result": {"error": "Empty request body"}}
                ]
            }

        body = json.loads(raw_body.decode("utf-8"))
        print(f"📩 Received Vapi webhook: {json.dumps(body, indent=2)}")

        # Vapi commonly wraps tool calls inside a top-level `message` object
        payload = body.get("message", body)
        
        # Check if this is a tool call
        if "toolCalls" in payload or "toolCall" in payload:
            return await handle_tool_call(payload)
        
        # Check if this is a function call (alternative format)
        if "function" in payload:
            return await handle_function_call(payload)
        
        # Unknown format
        return {
            "results": [
                {
                    "toolCallId": "unknown",
                    "result": {"status": "ignored", "message": "No actionable content found"},
                }
            ]
        }
        
    except Exception as e:
        print(f"❌ Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def handle_tool_call(body: dict):
    """Handle Vapi tool call format"""
    tool_calls = body.get("toolCalls", [])
    if not tool_calls and "toolCall" in body:
        tool_calls = [body["toolCall"]]
    
    results = []
    for tool_call in tool_calls:
        function_name = tool_call.get("function", {}).get("name")
        arguments = tool_call.get("function", {}).get("arguments", "{}")
        
        if isinstance(arguments, str):
            arguments = json.loads(arguments)
        
        tool_call_id = tool_call.get("id", "unknown")
        
        tool_result = await execute_tool(function_name, arguments, tool_call_id)

        # Vapi expects: { results: [ { toolCallId, result } ] }
        normalized = {
            "toolCallId": tool_call_id,
            "result": tool_result.get("result") if isinstance(tool_result, dict) else tool_result,
        }
        results.append(normalized)
    
    return {"results": results} if results else {"results": [{"toolCallId": "unknown", "result": {"status": "no_tools_executed"}}]}


async def handle_function_call(body: dict):
    """Handle alternative function call format"""
    function_name = body.get("function")
    arguments = body.get("arguments", {})
    
    if isinstance(arguments, str):
        arguments = json.loads(arguments)
    
    tool_result = await execute_tool(function_name, arguments, "direct")
    return {
        "results": [
            {
                "toolCallId": "direct",
                "result": tool_result.get("result") if isinstance(tool_result, dict) else tool_result,
            }
        ]
    }


async def execute_tool(function_name: str, arguments: dict, tool_call_id: str):
    """Execute the appropriate tool based on function name"""
    
    if function_name == "create_calendar_event":
        return await handle_create_calendar_event(arguments, tool_call_id)
    
    elif function_name == "parse_datetime":
        return await handle_parse_datetime(arguments, tool_call_id)
    
    else:
        return {
            "toolCallId": tool_call_id,
            "status": "error",
            "message": f"Unknown function: {function_name}"
        }


async def handle_create_calendar_event(arguments: dict, tool_call_id: str):
    """Create a calendar event"""
    try:
        title = arguments.get("title", "Meeting")
        start_datetime = arguments.get("start_datetime") or arguments.get("startIso")
        duration = arguments.get("duration_minutes") or arguments.get("durationMinutes", 30)
        timezone = arguments.get("timezone", "UTC")
        description = arguments.get("description", "Scheduled by Voice Assistant")
        
        print(f"📅 Creating event: {title} at {start_datetime}")
        
        # Parse the datetime if it's natural language
        # ISO datetimes typically include a `YYYY-MM-DDT...` segment.
        is_iso_datetime = bool(re.search(r"\d{4}-\d{2}-\d{2}T", str(start_datetime)))
        if not is_iso_datetime:
            parsed = parse_natural_datetime(str(start_datetime), timezone)
            start_datetime = parsed.get("startIso")
            if not start_datetime:
                raise ValueError(parsed.get("error") or f"Could not parse datetime: {start_datetime}")
        
        # Create the event
        event = create_calendar_event(
            title=title,
            start_datetime=start_datetime,
            duration_minutes=int(duration),
            timezone=timezone,
            description=description
        )
        
        return {
            "toolCallId": tool_call_id,
            "status": "success",
            "result": {
                "success": True,
                "eventId": event["id"],
                "htmlLink": event["htmlLink"],
                "summary": event["summary"],
                "start": event["start"]["dateTime"],
                "end": event["end"]["dateTime"]
            }
        }
        
    except Exception as e:
        print(f"❌ Error creating event: {str(e)}")
        return {
            "toolCallId": tool_call_id,
            "status": "error",
            "message": f"Failed to create event: {str(e)}"
        }


async def handle_parse_datetime(arguments: dict, tool_call_id: str):
    """Parse natural language datetime"""
    try:
        text = arguments.get("text", "")
        timezone = arguments.get("timezone", "UTC")
        
        result = parse_natural_datetime(text, timezone)
        
        return {
            "toolCallId": tool_call_id,
            "status": "success",
            "result": result
        }
        
    except Exception as e:
        return {
            "toolCallId": tool_call_id,
            "status": "error",
            "message": f"Failed to parse datetime: {str(e)}"
        }


@router.get("/test")
async def test_webhook():
    """Test endpoint to verify webhook is working"""
    return {"status": "webhook endpoint is active"}
