import os
import json
import base64
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from vision import analyze_frame
from yuhchat import trigger_security_call
from webhook import handle_tool_call

load_dotenv()

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# In-memory storage for incidents
incidents = []

# Jamaica timezone (UTC-5, no daylight saving)
JAMAICA_TZ = timezone(timedelta(hours=-5))


def jamaica_time():
    return datetime.now(JAMAICA_TZ).strftime("%I:%M %p")


def jamaica_datetime():
    return datetime.now(JAMAICA_TZ).strftime("%Y-%m-%d %I:%M %p")


# ============================
# PAGES
# ============================

@app.get("/ghostfence/camera", response_class=HTMLResponse)
async def camera_page(request: Request):
    return templates.TemplateResponse("camera.html", {"request": request})


@app.get("/ghostfence/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


# ============================
# CAMERA → VISION → YUHCHAT
# ============================

@app.post("/ghostfence/analyze-frame")
async def analyze_frame_endpoint(request: Request):
    """Receives a base64 frame from the camera, sends to Claude Vision."""
    body = await request.json()
    frame_data = body.get("frame")

    if not frame_data:
        return JSONResponse({"error": "No frame provided"}, status_code=400)

    # Remove data URL prefix if present
    if "," in frame_data:
        frame_data = frame_data.split(",")[1]

    # Analyze with Claude Vision
    result = analyze_frame(frame_data)

    # If person detected, trigger the call
    if result.get("person_detected"):
        alert_data = {
            "owner_name": os.getenv("OWNER_NAME", "Owner"),
            "owner_phone": os.getenv("OWNER_PHONE"),
            "people_count": result.get("people_count", 1),
            "description": result.get("description", "Unknown individual"),
            "location": result.get("location", "On property"),
            "timestamp": jamaica_time(),
            "detection_source": "Camera"
        }

        # Store incident
        incident = {
            "id": len(incidents) + 1,
            "timestamp": jamaica_datetime(),
            "source": "Camera",
            "description": result.get("description"),
            "people_count": result.get("people_count", 1),
            "location": result.get("location"),
            "status": "alert_sent",
            "outcome": "pending"
        }
        incidents.append(incident)

        # Trigger YuhChat call
        call_result = trigger_security_call(alert_data)

        return JSONResponse({
            "alert": True,
            "detection": result,
            "call_triggered": True,
            "incident_id": incident["id"]
        })

    return JSONResponse({
        "alert": False,
        "detection": result,
        "call_triggered": False
    })


# ============================
# RF SIMULATION
# ============================

@app.post("/ghostfence/simulate-rf")
async def simulate_rf(request: Request):
    """Simulates an RF sensor detecting motion. Triggered by dashboard button."""
    body = await request.json()

    zone = body.get("zone", "East perimeter")
    confidence = body.get("confidence", "high")

    incident = {
        "id": len(incidents) + 1,
        "timestamp": jamaica_datetime(),
        "source": "RF Sensor",
        "description": f"RF motion detected in {zone} (confidence: {confidence})",
        "people_count": "Unknown",
        "location": zone,
        "status": "rf_triggered",
        "outcome": "awaiting_visual_confirmation"
    }
    incidents.append(incident)

    return JSONResponse({
        "alert": True,
        "source": "rf_sensor",
        "zone": zone,
        "confidence": confidence,
        "timestamp": jamaica_time(),
        "message": "RF motion detected — activate visual verification",
        "incident_id": incident["id"]
    })


# ============================
# YUHCHAT WEBHOOK (TOOL CALLS)
# ============================

@app.post("/ghostfence/webhook")
async def webhook_endpoint(request: Request):
    """Handles all tool calls from both YuhChat agents."""
    payload = await request.json()
    result = handle_tool_call(payload, incidents)
    return JSONResponse(result)


# ============================
# INCIDENTS LOG
# ============================

@app.get("/ghostfence/incidents")
async def get_incidents():
    """Returns all incidents for the dashboard."""
    return JSONResponse({"incidents": list(reversed(incidents))})


# ============================
# HEALTH CHECK
# ============================

@app.get("/")
async def root():
    return {"status": "GhostFence is running", "time": jamaica_datetime()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
