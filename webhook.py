import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

JAMAICA_TZ = timezone(timedelta(hours=-5))


def handle_tool_call(payload: dict, incidents: list) -> dict:
    """Process incoming tool calls from YuhChat agents."""

    # Extract tool call info from the payload
    message = payload.get("message", {})
    tool_calls = message.get("toolCalls", [])

    if not tool_calls:
        # Try alternate payload structure
        tool_calls = message.get("tool_calls", [])

    if not tool_calls:
        return {"results": [{"result": "No tool call found in payload"}]}

    tool_call = tool_calls[0]
    function_info = tool_call.get("function", {})
    tool_name = function_info.get("name", "")
    tool_args = function_info.get("arguments", {})

    # If arguments is a string, parse it
    if isinstance(tool_args, str):
        import json
        try:
            tool_args = json.loads(tool_args)
        except:
            tool_args = {}

    # Route to the correct handler
    if tool_name == "escalate_to_security":
        return _handle_escalate_security(tool_args, incidents)

    elif tool_name == "escalate_to_police":
        return _handle_escalate_police(tool_args, incidents)

    elif tool_name == "stand_down":
        return _handle_stand_down(tool_args, incidents)

    elif tool_name == "log_incident":
        return _handle_log_incident(tool_args, incidents)

    elif tool_name == "check_incident_log":
        return _handle_check_incident_log(tool_args, incidents)

    elif tool_name == "update_contact":
        return _handle_update_contact(tool_args)

    elif tool_name == "system_status_check":
        return _handle_system_status(tool_args)

    else:
        return {"results": [{"result": f"Unknown tool: {tool_name}"}]}


def _handle_escalate_security(args: dict, incidents: list) -> dict:
    reason = args.get("reason", "Owner requested security")
    urgency = args.get("urgency", "high")

    # Update the latest incident
    if incidents:
        incidents[-1]["status"] = "escalated_security"
        incidents[-1]["outcome"] = f"Security contacted — {reason} (urgency: {urgency})"

    # In production, this would trigger a second outbound call
    # For demo, we just log it
    return {"results": [{"result": f"Security company has been contacted. Reason: {reason}. Urgency: {urgency}."}]}


def _handle_escalate_police(args: dict, incidents: list) -> dict:
    reason = args.get("reason", "Owner requested police")
    threat = args.get("threat_description", "Unknown threat")

    if incidents:
        incidents[-1]["status"] = "escalated_police"
        incidents[-1]["outcome"] = f"Police alerted — {reason}"

    return {"results": [{"result": f"Police have been alerted. Reason: {reason}. Threat: {threat}."}]}


def _handle_stand_down(args: dict, incidents: list) -> dict:
    reason = args.get("reason", "Owner confirmed activity is expected")

    if incidents:
        incidents[-1]["status"] = "resolved"
        incidents[-1]["outcome"] = f"Stood down — {reason}"

    return {"results": [{"result": f"Alert has been cleared. Reason: {reason}."}]}


def _handle_log_incident(args: dict, incidents: list) -> dict:
    outcome = args.get("outcome", "unknown")
    summary = args.get("owner_response_summary", "No summary")
    notes = args.get("notes", "")

    timestamp = datetime.now(JAMAICA_TZ).strftime("%Y-%m-%d %I:%M %p")

    if incidents:
        incidents[-1]["outcome"] = outcome
        incidents[-1]["owner_response"] = summary
        incidents[-1]["notes"] = notes
        incidents[-1]["logged_at"] = timestamp
    else:
        incidents.append({
            "id": 1,
            "timestamp": timestamp,
            "source": "Manual report",
            "outcome": outcome,
            "owner_response": summary,
            "notes": notes,
            "status": outcome
        })

    return {"results": [{"result": f"Incident logged successfully. Outcome: {outcome}."}]}


def _handle_check_incident_log(args: dict, incidents: list) -> dict:
    query = args.get("query", "")
    owner_id = args.get("owner_id", "")

    if not incidents:
        return {"results": [{"result": "No incidents found in the system."}]}

    # Search through incidents
    matches = []
    for inc in reversed(incidents):
        inc_str = str(inc).lower()
        if query.lower() in inc_str:
            matches.append(inc)
        if len(matches) >= 3:
            break

    # If no keyword match, return most recent
    if not matches:
        matches = incidents[-3:]

    result_text = ""
    for m in matches:
        result_text += f"Incident #{m.get('id')}: {m.get('timestamp')} — {m.get('description', 'No description')} — Source: {m.get('source', 'Unknown')} — Status: {m.get('status', 'Unknown')} — Outcome: {m.get('outcome', 'Pending')}. "

    return {"results": [{"result": result_text or "No matching incidents found."}]}


def _handle_update_contact(args: dict) -> dict:
    contact_type = args.get("contact_type", "unknown")
    new_value = args.get("new_value", "")
    owner_id = args.get("owner_id", "")

    # In production, this would update a database
    return {"results": [{"result": f"Contact updated. {contact_type} changed to {new_value} for owner {owner_id}."}]}


def _handle_system_status(args: dict) -> dict:
    owner_id = args.get("owner_id", "")

    # Return simulated system status
    return {"results": [{"result": "GhostFence system is active. RF sensing layer is online. Visual AI monitoring is standing by. All systems operational. Last check: just now."}]}
