
import tempfile
import os
import re
import json
import asyncio
import logging
import subprocess
from typing import Dict

import aiohttp
import requests

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware


# --- Configuration ---
DEEPGRAM_API_KEY = "9a0e91bb85ec065f6737054aa184728648c3de54"
DEEPGRAM_WS_URL = "wss://api.deepgram.com/v1/listen?encoding=mulaw&sample_rate=8000"
ELEVENLABS_API_KEY = "sk_e240470042f862f45d40083ef40fb5b7a8fba53e1295bdd8"
ELEVENLABS_VOICE_ID = "VR6AewLTigWG4xSOukaG"
LYZR_API_KEY = "sk-default-TRBUNs65fRohMoA0N338hYJUxSbIuOin"
LYZR_STREAM_ENDPOINT = "https://agent-prod.studio.lyzr.ai/v3/inference/stream/"
USER_ID = "prashant.rexha@gmail.com"
AGENT_ID = "67ef7a1f240aedef1b20cd20"
SESSION_ID = "67ef7a1f240aedef1b20cd20"


# --- Init ---
app = FastAPI()
logger = logging.getLogger("uvicorn")
logging.basicConfig(level=logging.INFO)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

response_sockets: Dict[str, WebSocket] = {}

def is_sentence_complete(text: str) -> bool:
    return bool(re.search(r"[.!?]$", text.strip()))

# def convert_to_mulaw(input_audio: bytes) -> bytes:
#     """Convert audio to mu-law encoding using ffmpeg."""
#     try:
#         # Convert raw audio to mu-law using ffmpeg
#         process = subprocess.Popen(
#             [
#                 "ffmpeg", "-f", "s16le", "-ar", "16000", "-ac", "1", "-i", "pipe:0", "-f", "mulaw", "pipe:1"
#             ],
#             stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
#         )

#         # Write audio to stdin
#         out, err = process.communicate(input=input_audio)
#         if process.returncode != 0:
#             logger.error(f"Error during ffmpeg conversion: {err.decode()}")
#             return None

#         return out
#     except Exception as e:
#         logger.error(f"Error converting audio to mu-law: {e}")
#         return None

DEEPGRAM_POST_URL = "https://api.deepgram.com/v1/listen"

@app.websocket("/ws/send_audio")
async def websocket_audio_input(websocket: WebSocket):
    await websocket.accept()
    logger.info("🎙️ Browser audio WebSocket connected")

    audio_buffer = b""

    try:
        while True:
            data = await websocket.receive_bytes()
            audio_buffer += data
            logger.info(f"📤 Received {len(data)} bytes (total {len(audio_buffer)})")

    except WebSocketDisconnect:
        logger.info("🔌 Browser audio WebSocket disconnected")
        logger.info("📨 Sending audio buffer to Deepgram...")

        try:
            # Send audio to Deepgram using POST
            headers = {
                "Authorization": f"Token {DEEPGRAM_API_KEY}",
                "Content-Type": "audio/webm"  # or audio/mulaw etc. depending on frontend format
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(DEEPGRAM_POST_URL, headers=headers, data=audio_buffer) as resp:
                    resp_json = await resp.json()
                    transcript = (
                        resp_json.get("results", {})
                        .get("channels", [{}])[0]
                        .get("alternatives", [{}])[0]
                        .get("transcript", "")
                    )

                    if transcript:
                        logger.info(f"📝 Deepgram transcript: {transcript}")
                        await stream_lyzr_response(transcript)
                    else:
                        logger.warning("⚠️ No transcript received")

        except Exception as e:
            logger.error(f"❌ Error during transcription: {e}")

# ----------------- LYZR STREAM -----------------
async def stream_lyzr_response(text: str):
    try:
        payload = {
            "user_id": USER_ID,
            "agent_id": AGENT_ID,
            "session_id": SESSION_ID,
            "message": text
        }
        headers = {
            "Content-Type": "application/json",
            "x-api-key": LYZR_API_KEY
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(LYZR_STREAM_ENDPOINT, headers=headers, json=payload) as resp:
                buffer = ""
                async for line in resp.content:
                    chunk = line.decode().strip()
                    if chunk.startswith("data: "):
                        word = chunk.replace("data: ", "")
                        if word == "[DONE]":
                            if buffer.strip():
                                await stream_to_elevenlabs(buffer.strip())
                            break

                        buffer += word
                        if is_sentence_complete(buffer):
                            sentence = buffer.strip()
                            logger.info(f"🗣️ Sending sentence to ElevenLabs: {sentence}")
                            await stream_to_elevenlabs(sentence)
                            buffer = ""
                            await asyncio.sleep(0.1)
    except Exception as e:
        logger.error(f"❌ Lyzr stream error: {e}")

# ----------------- ELEVENLABS STREAM -----------------
async def stream_to_elevenlabs(text: str):
    try:
        logger.info(f"🎧 Sending to ElevenLabs: {text}")
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
                },
                "output_format": "webm_opus"
            },
            stream=True
        )

        if response.status_code == 200:
            ws = next(iter(response_sockets.values()), None)
            if ws:
                logger.info("📡 Streaming audio to frontend")

                ffmpeg_process = subprocess.Popen(
                    [
                        "ffmpeg", "-hide_banner", "-loglevel", "error",
                        "-i", "pipe:0",
                        "-f", "webm", "-c:a", "libopus", "-b:a", "64k", "pipe:1"
                    ],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                )

                for chunk in response.iter_content(chunk_size=1024):
                    if chunk and ffmpeg_process.stdin:
                        try:
                            ffmpeg_process.stdin.write(chunk)
                            ffmpeg_process.stdin.flush()
                        except BrokenPipeError:
                            break

                if ffmpeg_process.stdin:
                    ffmpeg_process.stdin.close()

                while True:
                    data = ffmpeg_process.stdout.read(1024)
                    if not data:
                        break
                    await ws.send_bytes(data)

                ffmpeg_process.wait()

                logger.info(f"✅ Sent audio to frontend")

            else:
                logger.warning("⚠️ No active WebSocket to send audio")
        else:
            logger.error(f"❌ ElevenLabs error: {response.status_code} {response.text}")
    except Exception as e:
        logger.error(f"❌ Error streaming from ElevenLabs: {e}")


@app.websocket("/ws/send_text")
async def send_text(websocket: WebSocket):
    await websocket.accept()
    logger.info("📝 Text WebSocket connected")
    try:
        while True:
            message = await websocket.receive_text()
            logger.info(f"📨 Received text from frontend: {message}")
            await stream_lyzr_response(message)
    except WebSocketDisconnect:
        logger.info("🔌 Text WebSocket disconnected")

# ----------------- WS: AUDIO OUTPUT -----------------
@app.websocket("/ws/receive_audio")
async def receive_audio_ws(websocket: WebSocket):
    await websocket.accept()
    logger.info("🔊 Audio-output WebSocket connected")
    try:
        response_sockets["default"] = websocket
        while True:
            msg = await websocket.receive_text()
            logger.debug(f"🔁 Keep-alive received: {msg}")
    except WebSocketDisconnect:
        logger.info("🔌 Audio-output WebSocket disconnected")
        response_sockets.pop("default", None)

# ----------------- RUN -----------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
