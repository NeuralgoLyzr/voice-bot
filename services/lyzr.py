import os
import requests
from dotenv import load_dotenv

load_dotenv()

LYZR_API_KEY = os.getenv("LYZR_API_KEY")
LYZR_ENDPOINT = "https://agent-prod.studio.lyzr.ai/v3/inference/chat/"
USER_ID = os.getenv("USER_ID")
AGENT_ID = os.getenv("AGENT_ID")
SESSION_ID = os.getenv("SESSION_ID")

async def query_lyzr(message: str) -> str:
    try:
        payload = {
            "user_id": USER_ID,
            "agent_id": AGENT_ID,
            "session_id": SESSION_ID,
            "message": message
        }
        headers = {
            "Content-Type": "application/json",
            "x-api-key": LYZR_API_KEY
        }
        response = requests.post(LYZR_ENDPOINT, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json().get("response", "")
        print("❌ Lyzr error:", response.text)
    except Exception as e:
        print("❌ Lyzr exception:", e)
    return ""
