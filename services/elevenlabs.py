import os
import io
import requests
from dotenv import load_dotenv
from utils.audio_converter import convert_stream_to_ulaw
from base64 import b64encode
import json

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

async def stream_to_elevenlabs(text: str, websocket, stream_sid: str):
    try:
        response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}/stream",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "text": text,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.8
                }
            },
            stream=True
        )

        if response.status_code == 200:
            audio_buffer = io.BytesIO()
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    audio_buffer.write(chunk)
            audio_buffer.seek(0)
            ulaw_audio = convert_stream_to_ulaw(audio_buffer)
            await send_audio_response(websocket, ulaw_audio, stream_sid)
        else:
            print("❌ ElevenLabs API Error:", response.text)

    except Exception as e:
        print("❌ ElevenLabs error:", e)

async def send_audio_response(websocket, audio: bytes, stream_sid: str):
    try:
        audio_b64 = b64encode(audio).decode("utf-8")
        await websocket.send_text(json.dumps({
            "event": "media",
            "streamSid": stream_sid,
            "media": {"payload": audio_b64}
        }))
    except Exception as e:
        print("❌ Sending audio to Twilio failed:", e)
