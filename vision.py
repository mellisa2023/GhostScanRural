import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SECURITY_PROMPT = """You are a security camera AI analyst for GhostFence, a property security system.

Analyze this image and determine if any PEOPLE are present.

Respond ONLY with a JSON object, no other text, no markdown, no backticks:

If people are detected:
{
  "person_detected": true,
  "people_count": <number>,
  "description": "<what they look like — clothing, build, hair, distinguishing features>",
  "location": "<where in the frame — left side, center, near fence, by door, etc>",
  "activity": "<what they appear to be doing — walking, standing, climbing, running, crouching>",
  "threat_level": "<low/medium/high based on behavior and context>"
}

If no people detected:
{
  "person_detected": false,
  "people_count": 0,
  "description": "No people detected in frame",
  "location": "N/A",
  "activity": "N/A",
  "threat_level": "none"
}

Be specific and descriptive. This description will be spoken aloud to a property owner over the phone, so make it clear enough that they could identify the person."""


def analyze_frame(base64_image: str) -> dict:
    """Send a base64 image to Claude Vision and get security analysis."""
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": base64_image
                            }
                        },
                        {
                            "type": "text",
                            "text": SECURITY_PROMPT
                        }
                    ]
                }
            ]
        )

        # Parse the response
        raw_text = response.content[0].text.strip()

        # Clean up if wrapped in backticks
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1] if "\n" in raw_text else raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()

        result = json.loads(raw_text)
        return result

    except json.JSONDecodeError:
        return {
            "person_detected": False,
            "people_count": 0,
            "description": "Analysis error — could not parse response",
            "location": "N/A",
            "activity": "N/A",
            "threat_level": "none",
            "raw_response": raw_text
        }
    except Exception as e:
        return {
            "person_detected": False,
            "people_count": 0,
            "description": f"Vision API error: {str(e)}",
            "location": "N/A",
            "activity": "N/A",
            "threat_level": "none"
        }
