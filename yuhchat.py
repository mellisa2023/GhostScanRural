import os
import requests
from dotenv import load_dotenv

load_dotenv()

YUHCHAT_API_KEY = os.getenv("YUHCHAT_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")


def trigger_security_call(alert_data: dict) -> dict:
    """Trigger an outbound YuhChat call to the property owner with alert details."""
    try:
        response = requests.post(
            "https://api.vapi.ai/call/phone",
            headers={
                "Authorization": f"Bearer {YUHCHAT_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "assistantId": ASSISTANT_ID,
                "phoneNumberId": PHONE_NUMBER_ID,
                "customer": {
                    "number": alert_data["owner_phone"]
                },
                "assistantOverrides": {
                    "variableValues": {
                        "owner_name": alert_data.get("owner_name", "Owner"),
                        "people_count": str(alert_data.get("people_count", 1)),
                        "description": alert_data.get("description", "Unknown individual"),
                        "location": alert_data.get("location", "On property"),
                        "timestamp": alert_data.get("timestamp", "Unknown time"),
                        "detection_source": alert_data.get("detection_source", "Camera")
                    }
                }
            }
        )
        return response.json()

    except Exception as e:
        return {"error": str(e)}


def trigger_security_company_call(alert_data: dict, security_number: str) -> dict:
    """Trigger a second outbound call to the security company."""
    try:
        response = requests.post(
            "https://api.vapi.ai/call/phone",
            headers={
                "Authorization": f"Bearer {YUHCHAT_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "assistantId": ASSISTANT_ID,
                "phoneNumberId": PHONE_NUMBER_ID,
                "customer": {
                    "number": security_number
                },
                "assistantOverrides": {
                    "variableValues": {
                        "owner_name": "Security Dispatch",
                        "people_count": str(alert_data.get("people_count", 1)),
                        "description": alert_data.get("description", "Unknown individual"),
                        "location": alert_data.get("location", "On property"),
                        "timestamp": alert_data.get("timestamp", "Unknown time"),
                        "detection_source": alert_data.get("detection_source", "Camera")
                    }
                }
            }
        )
        return response.json()

    except Exception as e:
        return {"error": str(e)}
