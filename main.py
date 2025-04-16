# import asyncio
# import json
# import base64
# import aiohttp
# import requests
# import io
# import subprocess
# from fastapi import FastAPI, WebSocket
# from pydub import AudioSegment

# # --- Configuration ---
# DEEPGRAM_API_KEY = "9a0e91bb85ec065f6737054aa184728648c3de54"
# DEEPGRAM_WS_URL = "wss://api.deepgram.com/v1/listen?encoding=mulaw&sample_rate=8000"
# ELEVENLABS_API_KEY = "sk_e240470042f862f45d40083ef40fb5b7a8fba53e1295bdd8"
# ELEVENLABS_VOICE_ID = "VR6AewLTigWG4xSOukaG"
# LYZR_API_KEY = "sk-default-TRBUNs65fRohMoA0N338hYJUxSbIuOin"
# LYZR_ENDPOINT = "https://agent-prod.studio.lyzr.ai/v3/inference/chat/"
# USER_ID = "prashant.rexha@gmail.com"
# AGENT_ID = "67ef7a1f240aedef1b20cd20"
# SESSION_ID = "67ef7a1f240aedef1b20cd20"

# app = FastAPI()

# async def process_audio_stream(twilio_ws: WebSocket):
#     headers = [("Authorization", f"Token {DEEPGRAM_API_KEY}")]
#     stream_sid = None

#     async with aiohttp.ClientSession() as session:
#         async with session.ws_connect(DEEPGRAM_WS_URL, headers=headers) as dg_ws:
            
#             async def forward_twilio():
#                 nonlocal stream_sid
#                 try:
#                     while True:
#                         data = await twilio_ws.receive_text()
#                         message = json.loads(data)
#                         event = message.get("event")

#                         if event == "start":
#                             stream_sid = message.get("start", {}).get("streamSid")
#                             print(f"🔵 Twilio stream started: {stream_sid}")

#                         elif event == "media":
#                             audio_chunk = base64.b64decode(message["media"]["payload"])
#                             await dg_ws.send_bytes(audio_chunk)

#                         elif event == "stop":
#                             print("⏹️ Twilio stream stopped")
#                             await dg_ws.close()
#                             break

#                 except Exception as e:
#                     print("❌ Error receiving from Twilio:", e)

#             async def receive_from_deepgram():
#                 try:
#                     async for msg in dg_ws:
#                         if msg.type == aiohttp.WSMsgType.TEXT:
#                             transcript_data = json.loads(msg.data)
#                             if transcript_data.get("channel"):
#                                 alternatives = transcript_data["channel"].get("alternatives", [])
#                                 if alternatives:
#                                     transcript = alternatives[0].get("transcript", "")
#                                     if transcript:
#                                         print(f"📝 Got transcript: {transcript}")
#                                         lyzr_response = await query_lyzr(transcript)
#                                         if lyzr_response:
#                                             print(f"🧠 Lyzr response: {lyzr_response}")
#                                             await stream_to_elevenlabs(lyzr_response, twilio_ws, stream_sid)

#                         elif msg.type == aiohttp.WSMsgType.ERROR:
#                             print("❌ Deepgram WebSocket error:", msg)

#                 except Exception as e:
#                     print("❌ Error receiving from Deepgram:", e)

#             await asyncio.gather(forward_twilio(), receive_from_deepgram())

# async def query_lyzr(message: str) -> str:
#     try:
#         payload = {
#             "user_id": USER_ID,
#             "agent_id": AGENT_ID,
#             "session_id": SESSION_ID,
#             "message": message
#         }
#         headers = {
#             "Content-Type": "application/json",
#             "x-api-key": LYZR_API_KEY
#         }
#         response = requests.post(LYZR_ENDPOINT, headers=headers, json=payload)
#         if response.status_code == 200:
#             data = response.json()
#             return data.get("response", "")
#         else:
#             print(f"❌ Lyzr error: {response.status_code} {response.text}")
#             return ""
#     except Exception as e:
#         print(f"❌ Exception querying Lyzr: {e}")
#         return ""

# async def stream_to_elevenlabs(text: str, twilio_ws: WebSocket, stream_sid: str):
#     try:
#         response = requests.post(
#             f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}/stream",
#             headers={
#                 "xi-api-key": ELEVENLABS_API_KEY,
#                 "Content-Type": "application/json"
#             },
#             json={
#                 "text": text,
#                 "voice_settings": {
#                     "stability": 0.5,
#                     "similarity_boost": 0.8
#                 }
#             },
#             stream=True
#         )

#         if response.status_code == 200:
#             audio_buffer = io.BytesIO()
#             for chunk in response.iter_content(chunk_size=1024):
#                 if chunk:
#                     audio_buffer.write(chunk)

#             audio_buffer.seek(0)
#             ulaw_audio = convert_stream_to_ulaw(audio_buffer)

#             await send_audio_response(twilio_ws, ulaw_audio, stream_sid)
#         else:
#             print("❌ ElevenLabs API Error:", response.text)

#     except Exception as e:
#         print("❌ Error converting text to speech:", e)

# async def send_audio_response(twilio_ws: WebSocket, audio: bytes, stream_sid: str):
#     try:
#         audio_b64 = base64.b64encode(audio).decode("utf-8")
#         message = {
#             "event": "media",
#             "streamSid": stream_sid,
#             "media": {"payload": audio_b64}
#         }
#         await twilio_ws.send_text(json.dumps(message))
    
#     except Exception as e:
#         print("❌ Error sending audio to Twilio:", e)

# def convert_stream_to_ulaw(mp3_stream: io.BytesIO) -> bytes:
#     try:
#         audio_segment = AudioSegment.from_file(mp3_stream, format="mp3")
#         wav_buffer = io.BytesIO()
#         audio_segment.export(wav_buffer, format="wav")
#         wav_buffer.seek(0)

#         process = subprocess.run(
#             ["ffmpeg", "-i", "pipe:0", "-ar", "8000", "-ac", "1", "-acodec", "pcm_mulaw", "-f", "mulaw", "pipe:1"],
#             input=wav_buffer.read(),
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE
#         )

#         if process.returncode == 0:
#             print("✅ Converted to μ-law audio")
#             return process.stdout
#         else:
#             print(f"⚠️ FFmpeg error: {process.stderr.decode()}")
#             return b""
#     except Exception as e:
#         print(f"⚠️ Streaming conversion error: {e}")
#         return b""

# @app.websocket("/media")
# async def media_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     print("🔵 Twilio WebSocket connected")
#     await process_audio_stream(websocket)
#     await websocket.close()
#     print("🔴 WebSocket closed")

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)


import asyncio
import json
import base64
import aiohttp
import requests
import io
import subprocess
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydub import AudioSegment

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


app = FastAPI()

# async def process_audio_stream(twilio_ws: WebSocket):
#     headers = [("Authorization", f"Token {DEEPGRAM_API_KEY}")]
#     stream_sid = None

#     async with aiohttp.ClientSession() as session:
#         async with session.ws_connect(DEEPGRAM_WS_URL, headers=headers) as dg_ws:
            
#             async def forward_twilio():
#                 nonlocal stream_sid
#                 try:
#                     while True:
#                         data = await twilio_ws.receive_text()
#                         message = json.loads(data)
#                         event = message.get("event")

#                         if event == "start":
#                             stream_sid = message.get("start", {}).get("streamSid")
#                             print(f"🔵 Twilio stream started: {stream_sid}")

#                         elif event == "media":
#                             audio_chunk = base64.b64decode(message["media"]["payload"])
#                             await dg_ws.send_bytes(audio_chunk)

#                         elif event == "stop":
#                             print("⏹️ Twilio stream stopped")
#                             await dg_ws.close()
#                             break

#                 except Exception as e:
#                     print("❌ Error receiving from Twilio:", e)

#             async def receive_from_deepgram():
#                 try:
#                     async for msg in dg_ws:
#                         if msg.type == aiohttp.WSMsgType.TEXT:
#                             transcript_data = json.loads(msg.data)
#                             if transcript_data.get("channel"):
#                                 alternatives = transcript_data["channel"].get("alternatives", [])
#                                 if alternatives:
#                                     transcript = alternatives[0].get("transcript", "")
#                                     if transcript:
#                                         print(f"📝 Got transcript: {transcript}")
#                                         await stream_lyzr_response(transcript, twilio_ws, stream_sid)
#                         elif msg.type == aiohttp.WSMsgType.ERROR:
#                             print("❌ Deepgram WebSocket error:", msg)

#                 except Exception as e:
#                     print("❌ Error receiving from Deepgram:", e)

#             await asyncio.gather(forward_twilio(), receive_from_deepgram())

# async def stream_lyzr_response(text: str, twilio_ws: WebSocket, stream_sid: str):
#     try:
#         payload = {
#             "user_id": USER_ID,
#             "agent_id": AGENT_ID,
#             "session_id": SESSION_ID,
#             "message": text
#         }
#         headers = {
#             "Content-Type": "application/json",
#             "x-api-key": LYZR_API_KEY
#         }

#         async with aiohttp.ClientSession() as session:
#             async with session.post(LYZR_STREAM_ENDPOINT, headers=headers, json=payload) as resp:
#                 buffer = ""
#                 async for line in resp.content:
#                     chunk = line.decode().strip()
#                     if chunk.startswith("data: "):
#                         word = chunk.replace("data: ", "")
#                         if word == "[DONE]":
#                             if buffer:
#                                 await stream_to_elevenlabs(buffer.strip(), twilio_ws, stream_sid)
#                             break
#                         print(f"🧠 Lyzr chunk: {word}")
#                         buffer += word
#                         if word in [".", "?", "!"]:
#                             await stream_to_elevenlabs(buffer.strip(), twilio_ws, stream_sid)
#                             buffer = ""
#                             await asyncio.sleep(0.2)

#     except Exception as e:
#         print(f"❌ Error streaming from Lyzr: {e}")

# async def stream_to_elevenlabs(text: str, twilio_ws: WebSocket, stream_sid: str):
#     try:
#         response = requests.post(
#             f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}/stream",
#             headers={
#                 "xi-api-key": ELEVENLABS_API_KEY,
#                 "Content-Type": "application/json"
#             },
#             json={
#                 "text": text,
#                 "voice_settings": {
#                     "stability": 0.5,
#                     "similarity_boost": 0.8
#                 }
#             },
#             stream=True
#         )

#         if response.status_code == 200:
#             audio_buffer = io.BytesIO()
#             for chunk in response.iter_content(chunk_size=1024):
#                 if chunk:
#                     audio_buffer.write(chunk)

#             audio_buffer.seek(0)
#             ulaw_audio = convert_stream_to_ulaw(audio_buffer)

#             await send_audio_response(twilio_ws, ulaw_audio, stream_sid)
#         else:
#             print("❌ ElevenLabs API Error:", response.text)

#     except Exception as e:
#         print("❌ Error converting text to speech:", e)

# async def send_audio_response(twilio_ws: WebSocket, audio: bytes, stream_sid: str):
#     try:
#         audio_b64 = base64.b64encode(audio).decode("utf-8")
#         message = {
#             "event": "media",
#             "streamSid": stream_sid,
#             "media": {"payload": audio_b64}
#         }
#         await twilio_ws.send_text(json.dumps(message))

#         # Send "mark" to indicate end of segment
#         await twilio_ws.send_text(json.dumps({
#             "event": "mark",
#             "streamSid": stream_sid,
#             "mark": {"name": "end-of-segment"}
#         }))
#     except Exception as e:
#         if "closing transport" in str(e):
#             print("⚠️ Twilio closed the WebSocket. Stop sending audio.")
#         else:
#             print("❌ Error sending audio to Twilio:", e)

# def convert_stream_to_ulaw(mp3_stream: io.BytesIO) -> bytes:
#     try:
#         audio_segment = AudioSegment.from_file(mp3_stream, format="mp3")
#         wav_buffer = io.BytesIO()
#         audio_segment.export(wav_buffer, format="wav")
#         wav_buffer.seek(0)

#         process = subprocess.run(
#             ["ffmpeg", "-i", "pipe:0", "-ar", "8000", "-ac", "1", "-acodec", "pcm_mulaw", "-f", "mulaw", "pipe:1"],
#             input=wav_buffer.read(),
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE
#         )

#         if process.returncode == 0:
#             print("✅ Converted to μ-law audio")
#             return process.stdout
#         else:
#             print(f"⚠️ FFmpeg error: {process.stderr.decode()}")
#             return b""
#     except Exception as e:
#         print(f"⚠️ Streaming conversion error: {e}")
#         return b""

# @app.websocket("/media")
# async def media_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     print("🔵 Twilio WebSocket connected")
#     await process_audio_stream(websocket)
#     await websocket.close()
#     print("🔴 WebSocket closed")

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)


# app = FastAPI()

# async def process_audio_stream(twilio_ws: WebSocket):
#     headers = [("Authorization", f"Token {DEEPGRAM_API_KEY}")]
#     stream_sid = None
#     current_tts_task = None
#     tts_lock = asyncio.Lock()

#     async with aiohttp.ClientSession() as session:
#         async with session.ws_connect(DEEPGRAM_WS_URL, headers=headers) as dg_ws:

#             async def forward_twilio():
#                 nonlocal stream_sid, current_tts_task
#                 try:
#                     while True:
#                         data = await twilio_ws.receive_text()
#                         message = json.loads(data)
#                         event = message.get("event")

#                         if event == "start":
#                             stream_sid = message.get("start", {}).get("streamSid")
#                             print(f"🔵 Twilio stream started: {stream_sid}")

#                         elif event == "media":
#                             # Barge-in: cancel current TTS task
#                             async with tts_lock:
#                                 if current_tts_task and not current_tts_task.done():
#                                     current_tts_task.cancel()
#                                     print("🛑 Cancelled ongoing TTS due to user speech")

#                             audio_chunk = base64.b64decode(message["media"]["payload"])
#                             await dg_ws.send_bytes(audio_chunk)

#                         elif event == "stop":
#                             print("⏹️ Twilio stream stopped")
#                             await dg_ws.close()
#                             break

#                 except Exception as e:
#                     print("❌ Error receiving from Twilio:", e)

#             async def receive_from_deepgram():
#                 nonlocal current_tts_task
#                 try:
#                     async for msg in dg_ws:
#                         if msg.type == aiohttp.WSMsgType.TEXT:
#                             transcript_data = json.loads(msg.data)
#                             if transcript_data.get("channel"):
#                                 alternatives = transcript_data["channel"].get("alternatives", [])
#                                 if alternatives:
#                                     transcript = alternatives[0].get("transcript", "")
#                                     if transcript:
#                                         print(f"📝 Got transcript: {transcript}")
#                                         # Cancel previous TTS if still running
#                                         async with tts_lock:
#                                             if current_tts_task:
#                                                 current_tts_task.cancel()
#                                             current_tts_task = asyncio.create_task(
#                                                 stream_lyzr_response(transcript, twilio_ws, stream_sid)
#                                             )
#                         elif msg.type == aiohttp.WSMsgType.ERROR:
#                             print("❌ Deepgram WebSocket error:", msg)
#                 except Exception as e:
#                     print("❌ Error receiving from Deepgram:", e)

#             await asyncio.gather(forward_twilio(), receive_from_deepgram())


# async def stream_lyzr_response(text: str, twilio_ws: WebSocket, stream_sid: str):
#     try:
#         payload = {
#             "user_id": USER_ID,
#             "agent_id": AGENT_ID,
#             "session_id": SESSION_ID,
#             "message": text
#         }
#         headers = {
#             "Content-Type": "application/json",
#             "x-api-key": LYZR_API_KEY
#         }

#         async with aiohttp.ClientSession() as session:
#             async with session.post(LYZR_STREAM_ENDPOINT, headers=headers, json=payload) as resp:
#                 buffer = ""
#                 async for line in resp.content:
#                     chunk = line.decode().strip()
#                     if chunk.startswith("data: "):
#                         word = chunk.replace("data: ", "")
#                         if word == "[DONE]":
#                             if buffer:
#                                 await stream_to_elevenlabs(buffer.strip(), twilio_ws, stream_sid)
#                             break
#                         print(f"🧠 Lyzr chunk: {word}")
#                         buffer += word
#                         if word in [".", "!", "?"]:
#                             await stream_to_elevenlabs(buffer.strip(), twilio_ws, stream_sid)
#                             buffer = ""
#                             await asyncio.sleep(0.2)
#     except asyncio.CancelledError:
#         print("⚠️ Lyzr stream interrupted")
#     except Exception as e:
#         print(f"❌ Error in Lyzr stream: {e}")


# async def stream_to_elevenlabs(text: str, twilio_ws: WebSocket, stream_sid: str):
#     try:
#         response = requests.post(
#             f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}/stream",
#             headers={
#                 "xi-api-key": ELEVENLABS_API_KEY,
#                 "Content-Type": "application/json"
#             },
#             json={
#                 "text": text,
#                 "voice_settings": {
#                     "stability": 0.5,
#                     "similarity_boost": 0.8
#                 }
#             },
#             stream=True
#         )

#         if response.status_code == 200:
#             audio_buffer = io.BytesIO()
#             for chunk in response.iter_content(chunk_size=1024):
#                 audio_buffer.write(chunk)
#             audio_buffer.seek(0)

#             ulaw_audio = convert_stream_to_ulaw(audio_buffer)
#             await send_audio_response(twilio_ws, ulaw_audio, stream_sid)
#         else:
#             print("❌ ElevenLabs API error:", response.text)
#     except asyncio.CancelledError:
#         print("⚠️ ElevenLabs TTS interrupted")
#     except Exception as e:
#         print(f"❌ Error in ElevenLabs streaming: {e}")


# async def send_audio_response(twilio_ws: WebSocket, audio: bytes, stream_sid: str):
#     try:
#         audio_b64 = base64.b64encode(audio).decode("utf-8")
#         await twilio_ws.send_text(json.dumps({
#             "event": "media",
#             "streamSid": stream_sid,
#             "media": {"payload": audio_b64}
#         }))

#         await twilio_ws.send_text(json.dumps({
#             "event": "mark",
#             "streamSid": stream_sid,
#             "mark": {"name": "end-of-segment"}
#         }))
#     except Exception as e:
#         print("❌ Error sending audio to Twilio:", e)


# def convert_stream_to_ulaw(mp3_stream: io.BytesIO) -> bytes:
#     try:
#         audio_segment = AudioSegment.from_file(mp3_stream, format="mp3")
#         wav_buffer = io.BytesIO()
#         audio_segment.export(wav_buffer, format="wav")
#         wav_buffer.seek(0)

#         process = subprocess.run(
#             ["ffmpeg", "-i", "pipe:0", "-ar", "8000", "-ac", "1", "-acodec", "pcm_mulaw", "-f", "mulaw", "pipe:1"],
#             input=wav_buffer.read(),
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE
#         )

#         if process.returncode == 0:
#             print("✅ Converted to μ-law audio")
#             return process.stdout
#         else:
#             print("❌ FFmpeg conversion error:", process.stderr.decode())
#             return b""
#     except Exception as e:
#         print(f"⚠️ Audio conversion failed: {e}")
#         return b""


# @app.websocket("/media")
# async def media_endpoint(websocket: WebSocket):
#     await websocket.accept()
#     print("🔵 Twilio WebSocket connected")
#     await process_audio_stream(websocket)
#     await websocket.close()
#     print("🔴 WebSocket closed")


# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)

# from fastapi import FastAPI, WebSocket
# from fastapi.middleware.cors import CORSMiddleware
# import logging
# import aiohttp
# import asyncio
# import json
# from typing import Dict

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
# app = FastAPI()

# active_sessions = {}

# # Store response sockets
# response_sockets: Dict[str, WebSocket] = {}

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # 🎧 Receive audio from frontend & process with Deepgram
# async def stream_lyzr_response(text: str, session_id: str):
#     try:
#         payload = {
#             "user_id": USER_ID,
#             "agent_id": AGENT_ID,
#             "session_id": session_id,
#             "message": text
#         }
#         headers = {
#             "Content-Type": "application/json",
#             "x-api-key": LYZR_API_KEY
#         }

#         async with aiohttp.ClientSession() as session:
#             async with session.post(LYZR_STREAM_ENDPOINT, headers=headers, json=payload) as resp:
#                 buffer = ""
#                 async for line in resp.content:
#                     chunk = line.decode().strip()
#                     if chunk.startswith("data: "):
#                         word = chunk.replace("data: ", "")
#                         if word == "[DONE]":
#                             if buffer:
#                                 await stream_to_elevenlabs(buffer.strip(), session_id)
#                             break
#                         buffer += word
#                         if word in [".", "!", "?"]:
#                             await stream_to_elevenlabs(buffer.strip(), session_id)
#                             buffer = ""
#                             await asyncio.sleep(0.2)
#     except Exception as e:
#         logger.error(f"Lyzr stream error: {e}")

# # 🔊 Stream audio to frontend via ElevenLabs and ffmpeg
# async def stream_to_elevenlabs(text: str, session_id: str):
#     try:
#         logger.info(f"Sending to ElevenLabs: {text}")
#         response = requests.post(
#             f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}/stream",
#             headers={
#                 "xi-api-key": ELEVENLABS_API_KEY,
#                 "Content-Type": "application/json"
#             },
#             json={
#                 "text": text,
#                 "voice_settings": {
#                     "stability": 0.5,
#                     "similarity_boost": 0.8
#                 }
#             },
#             stream=True
#         )

#         if response.status_code == 200 and session_id in response_sockets:
#             ws = response_sockets[session_id]
#             logger.info("Connected to ElevenLabs. Starting FFmpeg.")

#             ffmpeg_process = subprocess.Popen(
#                 [
#                     "ffmpeg", "-hide_banner", "-loglevel", "error",
#                     "-i", "pipe:0",
#                     "-f", "webm", "-c:a", "libopus", "-b:a", "64k", "pipe:1"
#                 ],
#                 stdin=subprocess.PIPE,
#                 stdout=subprocess.PIPE,
#             )

#             async def feed_ffmpeg():
#                 for chunk in response.iter_content(chunk_size=1024):
#                     if chunk and ffmpeg_process.stdin:
#                         logger.info(f"Received {len(chunk)} bytes from ElevenLabs")
#                         ffmpeg_process.stdin.write(chunk)
#                         ffmpeg_process.stdin.flush()
#                 ffmpeg_process.stdin.close()

#             async def stream_to_frontend():
#                 while True:
#                     data = ffmpeg_process.stdout.read(1024)
#                     if not data:
#                         break
#                     logger.info(f"Streaming {len(data)} bytes to frontend WebSocket")
#                     await ws.send_bytes(data)

#             await asyncio.gather(feed_ffmpeg(), stream_to_frontend())
#             ffmpeg_process.wait()
#             logger.info("Done streaming to client.")
#         else:
#             logger.warning(f"Could not stream to client. Session {session_id} not found.")
#     except Exception as e:
#         logger.error(f"Error streaming from ElevenLabs: {e}")

# # 🛑 Send audio to Deepgram and handle transcription
# @app.websocket("/ws/send_audio")
# async def send_audio_ws(websocket: WebSocket):
#     await websocket.accept()
#     session_id = websocket.query_params.get("session_id")
#     if not session_id:
#         logger.error("Missing session_id in send_audio")
#         await websocket.close()
#         return

#     logger.info(f"Send-audio WebSocket connected | session_id={session_id}")

#     headers = [("Authorization", f"Token {DEEPGRAM_API_KEY}")]

#     async with aiohttp.ClientSession() as session:
#         try:
#             async with session.ws_connect(DEEPGRAM_WS_URL, headers=headers) as dg_ws:

#                 async def forward_audio():
#                     try:
#                         while True:
#                             data = await websocket.receive_bytes()
#                             logger.info(f"Received audio chunk from frontend: {len(data)} bytes")
#                             await dg_ws.send_bytes(data)
#                     except Exception as e:
#                         logger.error(f"Error receiving audio: {e}")

#                 async def handle_transcription():
#                     try:
#                         async for msg in dg_ws:
#                             if msg.type == aiohttp.WSMsgType.TEXT:
#                                 transcript_data = json.loads(msg.data)
#                                 if transcript_data.get("channel"):
#                                     alternatives = transcript_data["channel"].get("alternatives", [])
#                                     if alternatives:
#                                         transcript = alternatives[0].get("transcript", "")
#                                         if transcript:
#                                             logger.info(f"Transcript from Deepgram: \"{transcript}\"")
#                                             await stream_lyzr_response(transcript, session_id)
#                     except Exception as e:
#                         logger.error(f"Transcription error: {e}")

#                 await asyncio.gather(forward_audio(), handle_transcription())

#         except Exception as e:
#             logger.error(f"Deepgram connection error: {e}")

# # 🔈 Receive audio stream and forward it to client
# @app.websocket("/ws/receive_audio")
# async def receive_audio_ws(websocket: WebSocket):
#     await websocket.accept()
#     session_id = websocket.query_params.get("session_id")
#     if not session_id:
#         logger.error("Missing session_id in receive_audio")
#         await websocket.close()
#         return

#     logger.info(f"Receive-audio WebSocket connected | session_id={session_id}")
#     try:
#         response_sockets[session_id] = websocket
#         while True:
#             msg = await websocket.receive_text()  # Just for keep-alive
#             logger.debug(f"Keep-alive or control message received: {msg}")
#     except WebSocketDisconnect:
#         logger.info("Receive-audio WebSocket disconnected")
#         response_sockets.pop(session_id, None)

# # ▶️ Start app
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)








# import asyncio
# import json
# import aiohttp
# import requests
# import subprocess
# import logging
# from fastapi import FastAPI, WebSocket, WebSocketDisconnect
# from fastapi.middleware.cors import CORSMiddleware
# from typing import Dict
# import os

# # ----------------- CONFIG -----------------
# DEEPGRAM_API_KEY = "your_deepgram_api_key"
# ELEVENLABS_API_KEY = "sk_e240470042f862f45d40083ef40fb5b7a8fba53e1295bdd8"
# ELEVENLABS_VOICE_ID = "VR6AewLTigWG4xSOukaG"
# LYZR_API_KEY = "sk-default-TRBUNs65fRohMoA0N338hYJUxSbIuOin"
# LYZR_STREAM_ENDPOINT = "https://agent-prod.studio.lyzr.ai/v3/inference/stream/"
# USER_ID = "prashant.rexha@gmail.com"
# AGENT_ID = "67ef7a1f240aedef1b20cd20"
# SESSION_ID = "67ef7a1f240aedef1b20cd20"


# # ----------------- SETUP -----------------
# app = FastAPI()
# logger = logging.getLogger("uvicorn")
# logging.basicConfig(level=logging.INFO)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# response_sockets: Dict[str, WebSocket] = {}

# # --------- AUDIO SAVE FOR DEBUGGING ---------
# def save_audio_to_file(audio_bytes: bytes, session_id: str = "default_session"):
#     output_dir = "saved_audio"
#     os.makedirs(output_dir, exist_ok=True)
#     file_path = os.path.join(output_dir, f"{session_id}.webm")
#     with open(file_path, "wb") as f:
#         f.write(audio_bytes)
#     logger.info(f"✅ Audio saved to {file_path}")
#     return file_path

# # ----------------- LYZR STREAM -----------------
# import re

# # Helper: Detect if sentence seems complete
# def is_sentence_complete(text: str) -> bool:
#     return bool(re.search(r"[.!?]$", text.strip()))

# async def stream_lyzr_response(text: str, session_id: str):
#     try:
#         payload = {
#             "user_id": USER_ID,
#             "agent_id": AGENT_ID,
#             "session_id": session_id,
#             "message": text
#         }
#         headers = {
#             "Content-Type": "application/json",
#             "x-api-key": LYZR_API_KEY
#         }

#         async with aiohttp.ClientSession() as session:
#             async with session.post(LYZR_STREAM_ENDPOINT, headers=headers, json=payload) as resp:
#                 buffer = ""
#                 async for line in resp.content:
#                     chunk = line.decode().strip()
#                     if chunk.startswith("data: "):
#                         word = chunk.replace("data: ", "")
#                         if word == "[DONE]":
#                             if buffer.strip():
#                                 await stream_to_elevenlabs(buffer.strip(), session_id)
#                             break

#                         buffer += word
#                         if is_sentence_complete(buffer):
#                             sentence = buffer.strip()
#                             logger.info(f"📤 Sending sentence to ElevenLabs: {sentence}")
#                             await stream_to_elevenlabs(sentence, session_id)
#                             buffer = ""
#                             await asyncio.sleep(0.2)  # Small pacing delay to avoid overlap
#     except Exception as e:
#         logger.error(f"Lyzr stream error: {e}")

# # ----------------- ELEVENLABS STREAM -----------------
# async def stream_to_elevenlabs(text: str, session_id: str):
#     try:
#         logger.info(f"Sending to ElevenLabs: {text}")
#         response = requests.post(
#             f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}/stream",
#             headers={
#                 "xi-api-key": ELEVENLABS_API_KEY,
#                 "Content-Type": "application/json"
#             },
#             json={
#                 "text": text,
#                 "voice_settings": {
#                     "stability": 0.5,
#                     "similarity_boost": 0.8
#                 }
#             },
#             stream=True
#         )

#         if response.status_code == 200 and session_id in response_sockets:
#             ws = response_sockets[session_id]
#             logger.info("Connected to ElevenLabs. Starting FFmpeg.")

#             ffmpeg_process = subprocess.Popen(
#                 [
#                     "ffmpeg", "-hide_banner", "-loglevel", "error",
#                     "-i", "pipe:0",
#                     "-f", "webm", "-c:a", "libopus", "-b:a", "64k", "pipe:1"
#                 ],
#                 stdin=subprocess.PIPE,
#                 stdout=subprocess.PIPE,
#             )

#             audio_accumulator = b''

#             # Feed ElevenLabs audio into FFmpeg
#             for chunk in response.iter_content(chunk_size=1024):
#                 if chunk and ffmpeg_process.stdin:
#                     ffmpeg_process.stdin.write(chunk)
#                     ffmpeg_process.stdin.flush()

#             if ffmpeg_process.stdin:
#                 ffmpeg_process.stdin.close()

#             # Collect FFmpeg output
#             while True:
#                 data = ffmpeg_process.stdout.read(1024)
#                 if not data:
#                     break
#                 audio_accumulator += data

#             ffmpeg_process.wait()

#             # Save for debugging
#             save_audio_to_file(audio_accumulator, session_id)

#             # Send full audio blob to frontend
#             await ws.send_bytes(audio_accumulator)
#             logger.info(f"✅ Sent full audio blob to frontend: {len(audio_accumulator)} bytes")

#         else:
#             logger.warning(f"Could not stream to client. Session {session_id} not found.")
#     except Exception as e:
#         logger.error(f"Error streaming from ElevenLabs: {e}")

# # ----------------- WS: TEXT INPUT -----------------
# @app.websocket("/ws/send_text")
# async def send_text_ws(websocket: WebSocket):
#     await websocket.accept()
#     logger.info(f"Send-text WebSocket connected | session_id={SESSION_ID}")
#     try:
#         while True:
#             data = await websocket.receive_text()
#             logger.info(f"Received text from frontend: {data}")
#             await stream_lyzr_response(data, SESSION_ID)
#     except WebSocketDisconnect:
#         logger.info("Send-text WebSocket disconnected")

# # ----------------- WS: AUDIO OUTPUT -----------------
# @app.websocket("/ws/receive_audio")
# async def receive_audio_ws(websocket: WebSocket):
#     await websocket.accept()
#     logger.info(f"Receive-audio WebSocket connected | session_id={SESSION_ID}")
#     try:
#         response_sockets[SESSION_ID] = websocket
#         while True:
#             msg = await websocket.receive_text()  # For keep-alive
#             logger.debug(f"Keep-alive or control message received: {msg}")
#     except WebSocketDisconnect:
#         logger.info("Receive-audio WebSocket disconnected")
#         response_sockets.pop(SESSION_ID, None)

# # ----------------- RUN SERVER -----------------
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)












# import asyncio
# import json
# import aiohttp
# import requests
# import subprocess
# import logging
# from fastapi import FastAPI, WebSocket, WebSocketDisconnect
# from fastapi.middleware.cors import CORSMiddleware
# from typing import Dict
# import os
# import re

# # ----------------- CONFIG -----------------
# DEEPGRAM_API_KEY = "your_deepgram_api_key"
# ELEVENLABS_API_KEY = "sk_e240470042f862f45d40083ef40fb5b7a8fba53e1295bdd8"
# ELEVENLABS_VOICE_ID = "VR6AewLTigWG4xSOukaG"
# LYZR_API_KEY = "sk-default-TRBUNs65fRohMoA0N338hYJUxSbIuOin"
# LYZR_STREAM_ENDPOINT = "https://agent-prod.studio.lyzr.ai/v3/inference/stream/"
# USER_ID = "prashant.rexha@gmail.com"
# AGENT_ID = "67ef7a1f240aedef1b20cd20"
# SESSION_ID = "67ef7a1f240aedef1b20cd20"

# # ----------------- SETUP -----------------
# app = FastAPI()
# logger = logging.getLogger("uvicorn")
# logging.basicConfig(level=logging.INFO)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# response_sockets: Dict[str, WebSocket] = {}
# session_tasks: Dict[str, asyncio.Task] = {}

# # ----------------- AUDIO SAVE FOR DEBUGGING -----------------
# def save_audio_to_file(audio_bytes: bytes, session_id: str = "default_session"):
#     output_dir = "saved_audio"
#     os.makedirs(output_dir, exist_ok=True)
#     file_path = os.path.join(output_dir, f"{session_id}.webm")
#     with open(file_path, "wb") as f:
#         f.write(audio_bytes)
#     logger.info(f"✅ Audio saved to {file_path}")
#     return file_path

# # ----------------- HELPER -----------------
# def is_sentence_complete(text: str) -> bool:
#     return bool(re.search(r"[.!?]$", text.strip()))

# # ----------------- LYZR STREAM -----------------
# async def stream_lyzr_response(text: str, session_id: str):
#     try:
#         payload = {
#             "user_id": USER_ID,
#             "agent_id": AGENT_ID,
#             "session_id": session_id,
#             "message": text
#         }
#         headers = {
#             "Content-Type": "application/json",
#             "x-api-key": LYZR_API_KEY
#         }

#         async with aiohttp.ClientSession() as session:
#             async with session.post(LYZR_STREAM_ENDPOINT, headers=headers, json=payload) as resp:
#                 buffer = ""
#                 async for line in resp.content:
#                     try:
#                         chunk = line.decode().strip()
#                         if chunk.startswith("data: "):
#                             word = chunk.replace("data: ", "")
#                             if word == "[DONE]":
#                                 if buffer.strip():
#                                     await stream_to_elevenlabs(buffer.strip(), session_id)
#                                 break

#                             buffer += word
#                             if is_sentence_complete(buffer):
#                                 sentence = buffer.strip()
#                                 logger.info(f"📤 Sending sentence to ElevenLabs: {sentence}")
#                                 await stream_to_elevenlabs(sentence, session_id)
#                                 buffer = ""
#                                 await asyncio.sleep(0.2)
#                     except asyncio.CancelledError:
#                         logger.warning(f"🛑 Lyzr stream task was cancelled | session_id={session_id}")
#                         raise
#     except asyncio.CancelledError:
#         logger.warning(f"🛑 Lyzr response stream cancelled mid-way | session_id={session_id}")
#         raise
#     except Exception as e:
#         logger.error(f"Lyzr stream error: {e}")

# # ----------------- ELEVENLABS STREAM -----------------
# async def stream_to_elevenlabs(text: str, session_id: str):
#     try:
#         logger.info(f"Sending to ElevenLabs: {text}")
#         response = requests.post(
#             f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}/stream",
#             headers={
#                 "xi-api-key": ELEVENLABS_API_KEY,
#                 "Content-Type": "application/json"
#             },
#             json={
#                 "text": text,
#                 "voice_settings": {
#                     "stability": 0.5,
#                     "similarity_boost": 0.8
#                 }
#             },
#             stream=True
#         )

#         if response.status_code == 200 and session_id in response_sockets:
#             ws = response_sockets[session_id]
#             logger.info("Connected to ElevenLabs. Starting FFmpeg.")

#             ffmpeg_process = subprocess.Popen(
#                 [
#                     "ffmpeg", "-hide_banner", "-loglevel", "error",
#                     "-i", "pipe:0",
#                     "-f", "webm", "-c:a", "libopus", "-b:a", "64k", "pipe:1"
#                 ],
#                 stdin=subprocess.PIPE,
#                 stdout=subprocess.PIPE,
#             )

#             audio_accumulator = b''

#             for chunk in response.iter_content(chunk_size=1024):
#                 try:
#                     if chunk and ffmpeg_process.stdin:
#                         ffmpeg_process.stdin.write(chunk)
#                         ffmpeg_process.stdin.flush()
#                 except BrokenPipeError:
#                     break

#             if ffmpeg_process.stdin:
#                 ffmpeg_process.stdin.close()

#             while True:
#                 data = ffmpeg_process.stdout.read(1024)
#                 if not data:
#                     break
#                 audio_accumulator += data

#             ffmpeg_process.wait()

#             save_audio_to_file(audio_accumulator, session_id)

#             await ws.send_bytes(audio_accumulator)
#             logger.info(f"✅ Sent full audio blob to frontend: {len(audio_accumulator)} bytes")
#         else:
#             logger.warning(f"Could not stream to client. Session {session_id} not found.")
#     except asyncio.CancelledError:
#         logger.warning(f"🛑 ElevenLabs stream cancelled | session_id={session_id}")
#         raise
#     except Exception as e:
#         logger.error(f"Error streaming from ElevenLabs: {e}")

# # ----------------- WS: TEXT INPUT -----------------
# @app.websocket("/ws/send_text")
# async def send_text_ws(websocket: WebSocket):
#     await websocket.accept()
#     logger.info(f"Send-text WebSocket connected | session_id={SESSION_ID}")
#     try:
#         while True:
#             data = await websocket.receive_text()
#             logger.info(f"🆕 New message received: {data}")

#             # Cancel previous task if any
#             old_task = session_tasks.get(SESSION_ID)
#             if old_task and not old_task.done():
#                 logger.info(f"🛑 Cancelling previous task for session {SESSION_ID}")
#                 old_task.cancel()
#                 try:
#                     await old_task
#                 except asyncio.CancelledError:
#                     logger.info("✅ Previous task cancelled")

#             # Start new task
#             task = asyncio.create_task(stream_lyzr_response(data, SESSION_ID))
#             session_tasks[SESSION_ID] = task
#     except WebSocketDisconnect:
#         logger.info("Send-text WebSocket disconnected")
#         session_tasks.pop(SESSION_ID, None)

# # ----------------- WS: AUDIO OUTPUT -----------------
# @app.websocket("/ws/receive_audio")
# async def receive_audio_ws(websocket: WebSocket):
#     await websocket.accept()
#     logger.info(f"Receive-audio WebSocket connected | session_id={SESSION_ID}")
#     try:
#         response_sockets[SESSION_ID] = websocket
#         while True:
#             msg = await websocket.receive_text()  # For keep-alive or control
#             logger.debug(f"Keep-alive message received: {msg}")
#     except WebSocketDisconnect:
#         logger.info("Receive-audio WebSocket disconnected")
#         response_sockets.pop(SESSION_ID, None)

# # ----------------- RUN SERVER -----------------
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)







# #working code

# import asyncio
# import json
# import aiohttp
# import requests
# import subprocess
# import logging
# from fastapi import FastAPI, WebSocket, WebSocketDisconnect
# from fastapi.middleware.cors import CORSMiddleware
# from typing import Dict
# import os
# import re

# # ----------------- CONFIG -----------------
# DEEPGRAM_API_KEY = "your_deepgram_api_key"
# ELEVENLABS_API_KEY = "sk_e240470042f862f45d40083ef40fb5b7a8fba53e1295bdd8"
# ELEVENLABS_VOICE_ID = "VR6AewLTigWG4xSOukaG"
# LYZR_API_KEY = "sk-default-TRBUNs65fRohMoA0N338hYJUxSbIuOin"
# LYZR_STREAM_ENDPOINT = "https://agent-prod.studio.lyzr.ai/v3/inference/stream/"
# USER_ID = "prashant.rexha@gmail.com"
# AGENT_ID = "67ef7a1f240aedef1b20cd20"

# # ----------------- SETUP -----------------
# app = FastAPI()
# logger = logging.getLogger("uvicorn")
# logging.basicConfig(level=logging.INFO)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# response_sockets: Dict[str, WebSocket] = {}

# # ----------------- AUDIO SAVE FOR DEBUGGING -----------------
# def save_audio_to_file(audio_bytes: bytes):
#     output_dir = "saved_audio"
#     os.makedirs(output_dir, exist_ok=True)
#     file_path = os.path.join(output_dir, f"output.webm")
#     with open(file_path, "wb") as f:
#         f.write(audio_bytes)
#     logger.info(f"✅ Audio saved to {file_path}")
#     return file_path

# # ----------------- HELPER -----------------
# def is_sentence_complete(text: str) -> bool:
#     return bool(re.search(r"[.!?]$", text.strip()))

# # ----------------- LYZR STREAM -----------------
# async def stream_lyzr_response(text: str):
#     try:
#         payload = {
#             "user_id": USER_ID,
#             "agent_id": AGENT_ID,
#             "session_id": SESSION_ID,  
#             "message": text
#         }
#         headers = {
#             "Content-Type": "application/json",
#             "x-api-key": LYZR_API_KEY
#         }

#         async with aiohttp.ClientSession() as session:
#             async with session.post(LYZR_STREAM_ENDPOINT, headers=headers, json=payload) as resp:
#                 buffer = ""
#                 async for line in resp.content:
#                     chunk = line.decode().strip()
#                     if chunk.startswith("data: "):
#                         word = chunk.replace("data: ", "")
#                         if word == "[DONE]":
#                             if buffer.strip():
#                                 await stream_to_elevenlabs(buffer.strip())
#                             break

#                         buffer += word
#                         if is_sentence_complete(buffer):
#                             sentence = buffer.strip()
#                             logger.info(f"📤 Sending sentence to ElevenLabs: {sentence}")
#                             await stream_to_elevenlabs(sentence)
#                             buffer = ""
#                             await asyncio.sleep(0.2)
#     except Exception as e:
#         logger.error(f"Lyzr stream error: {e}")

# # ----------------- ELEVENLABS STREAM -----------------
# async def stream_to_elevenlabs(text: str):
#     try:
#         logger.info(f"Sending to ElevenLabs: {text}")
#         response = requests.post(
#             f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}/stream",
#             headers={
#                 "xi-api-key": ELEVENLABS_API_KEY,
#                 "Content-Type": "application/json"
#             },
#             json={
#                 "text": text,
#                 "voice_settings": {
#                     "stability": 0.5,
#                     "similarity_boost": 0.8
#                 }
#             },
#             stream=True
#         )

#         if response.status_code == 200:
#             ws = next(iter(response_sockets.values()), None)
#             if ws:
#                 logger.info("Connected to ElevenLabs. Starting FFmpeg.")

#                 ffmpeg_process = subprocess.Popen(
#                     [
#                         "ffmpeg", "-hide_banner", "-loglevel", "error",
#                         "-i", "pipe:0",
#                         "-f", "webm", "-c:a", "libopus", "-b:a", "64k", "pipe:1"
#                     ],
#                     stdin=subprocess.PIPE,
#                     stdout=subprocess.PIPE,
#                 )

#                 audio_accumulator = b''

#                 for chunk in response.iter_content(chunk_size=1024):
#                     if chunk and ffmpeg_process.stdin:
#                         try:
#                             ffmpeg_process.stdin.write(chunk)
#                             ffmpeg_process.stdin.flush()
#                         except BrokenPipeError:
#                             break

#                 if ffmpeg_process.stdin:
#                     ffmpeg_process.stdin.close()

#                 while True:
#                     data = ffmpeg_process.stdout.read(1024)
#                     if not data:
#                         break
#                     audio_accumulator += data

#                 ffmpeg_process.wait()

#                 save_audio_to_file(audio_accumulator)

#                 await ws.send_bytes(audio_accumulator)
#                 logger.info(f"✅ Sent full audio blob to frontend: {len(audio_accumulator)} bytes")
#             else:
#                 logger.warning("No active WebSocket to send audio")
#     except Exception as e:
#         logger.error(f"Error streaming from ElevenLabs: {e}")

# # ----------------- WS: TEXT INPUT -----------------
# @app.websocket("/ws/send_text")
# async def send_text_ws(websocket: WebSocket):
#     await websocket.accept()
#     logger.info("Send-text WebSocket connected")
#     try:
#         while True:
#             data = await websocket.receive_text()
#             logger.info(f"🆕 New message received: {data}")
#             await stream_lyzr_response(data)
#     except WebSocketDisconnect:
#         logger.info("Send-text WebSocket disconnected")

# # ----------------- WS: AUDIO OUTPUT -----------------
# @app.websocket("/ws/receive_audio")
# async def receive_audio_ws(websocket: WebSocket):
#     await websocket.accept()
#     logger.info("Receive-audio WebSocket connected")
#     try:
#         response_sockets["default"] = websocket
#         while True:
#             msg = await websocket.receive_text()  # For keep-alive
#             logger.debug(f"Keep-alive message received: {msg}")
#     except WebSocketDisconnect:
#         logger.info("Receive-audio WebSocket disconnected")
#         response_sockets.pop("default", None)

# # ----------------- RUN SERVER -----------------
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)


# import asyncio
# import json
# import aiohttp
# import requests
# import subprocess
# import logging
# from fastapi import FastAPI, WebSocket, WebSocketDisconnect
# from fastapi.middleware.cors import CORSMiddleware
# from typing import Dict
# import os
# import re

# # ----------------- CONFIG -----------------
# DEEPGRAM_API_KEY = "your_deepgram_api_key"
# ELEVENLABS_API_KEY = "sk_e240470042f862f45d40083ef40fb5b7a8fba53e1295bdd8"
# ELEVENLABS_VOICE_ID = "VR6AewLTigWG4xSOukaG"
# LYZR_API_KEY = "sk-default-TRBUNs65fRohMoA0N338hYJUxSbIuOin"
# LYZR_STREAM_ENDPOINT = "https://agent-prod.studio.lyzr.ai/v3/inference/stream/"
# USER_ID = "prashant.rexha@gmail.com"
# AGENT_ID = "67ef7a1f240aedef1b20cd20"

# # ----------------- SETUP -----------------
# app = FastAPI()
# logger = logging.getLogger("uvicorn")
# logging.basicConfig(level=logging.INFO)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# response_sockets: Dict[str, WebSocket] = {}

# # ----------------- AUDIO SAVE FOR DEBUGGING -----------------
# def save_audio_to_file(audio_bytes: bytes):
#     output_dir = "saved_audio"
#     os.makedirs(output_dir, exist_ok=True)
#     file_path = os.path.join(output_dir, f"output.webm")
#     with open(file_path, "wb") as f:
#         f.write(audio_bytes)
#     logger.info(f"✅ Audio saved to {file_path}")
#     return file_path

# # ----------------- HELPER -----------------
# def is_sentence_complete(text: str) -> bool:
#     return bool(re.search(r"[.!?]$", text.strip()))

# # ----------------- LYZR STREAM -----------------
# async def stream_lyzr_response(text: str):
#     try:
#         payload = {
#             "user_id": USER_ID,
#             "agent_id": AGENT_ID,
#             "session_id": SESSION_ID,  
#             "message": text
#         }
#         headers = {
#             "Content-Type": "application/json",
#             "x-api-key": LYZR_API_KEY
#         }

#         async with aiohttp.ClientSession() as session:
#             async with session.post(LYZR_STREAM_ENDPOINT, headers=headers, json=payload) as resp:
#                 buffer = ""
#                 async for line in resp.content:
#                     chunk = line.decode().strip()
#                     if chunk.startswith("data: "):
#                         word = chunk.replace("data: ", "")
#                         if word == "[DONE]":
#                             if buffer.strip():
#                                 await stream_to_elevenlabs(buffer.strip())
#                             break

#                         buffer += word
#                         if is_sentence_complete(buffer):
#                             sentence = buffer.strip()
#                             logger.info(f"📤 Sending sentence to ElevenLabs: {sentence}")
#                             await stream_to_elevenlabs(sentence)
#                             buffer = ""
#                             await asyncio.sleep(0.2)
#     except Exception as e:
#         logger.error(f"Lyzr stream error: {e}")

# # ----------------- ELEVENLABS STREAM -----------------
# async def stream_to_elevenlabs(text: str):
#     try:
#         logger.info(f"Sending to ElevenLabs: {text}")
#         response = requests.post(
#             f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}/stream",
#             headers={
#                 "xi-api-key": ELEVENLABS_API_KEY,
#                 "Content-Type": "application/json"
#             },
#             json={
#                 "text": text,
#                 "voice_settings": {
#                     "stability": 0.5,
#                     "similarity_boost": 0.8
#                 }
#             },
#             stream=True
#         )

#         if response.status_code == 200:
#             ws = next(iter(response_sockets.values()), None)
#             if ws:
#                 logger.info("Connected to ElevenLabs. Starting FFmpeg.")

#                 ffmpeg_process = subprocess.Popen(
#                     [
#                         "ffmpeg", "-hide_banner", "-loglevel", "error",
#                         "-i", "pipe:0",
#                         "-f", "webm", "-c:a", "libopus", "-b:a", "64k", "pipe:1"
#                     ],
#                     stdin=subprocess.PIPE,
#                     stdout=subprocess.PIPE,
#                 )

#                 audio_accumulator = b''

#                 for chunk in response.iter_content(chunk_size=1024):
#                     if chunk and ffmpeg_process.stdin:
#                         try:
#                             ffmpeg_process.stdin.write(chunk)
#                             ffmpeg_process.stdin.flush()
#                         except BrokenPipeError:
#                             break

#                 if ffmpeg_process.stdin:
#                     ffmpeg_process.stdin.close()

#                 while True:
#                     data = ffmpeg_process.stdout.read(1024)
#                     if not data:
#                         break
#                     audio_accumulator += data

#                 ffmpeg_process.wait()

#                 save_audio_to_file(audio_accumulator)

#                 await ws.send_bytes(audio_accumulator)
#                 logger.info(f"✅ Sent full audio blob to frontend: {len(audio_accumulator)} bytes")
#             else:
#                 logger.warning("No active WebSocket to send audio")
#     except Exception as e:
#         logger.error(f"Error streaming from ElevenLabs: {e}")

# # ----------------- WS: TEXT INPUT -----------------
# @app.websocket("/ws/send_text")
# async def send_text_ws(websocket: WebSocket):
#     await websocket.accept()
#     logger.info("Send-text WebSocket connected")
#     try:
#         while True:
#             data = await websocket.receive_text()
#             logger.info(f"🆕 New message received: {data}")
#             await stream_lyzr_response(data)
#     except WebSocketDisconnect:
#         logger.info("Send-text WebSocket disconnected")

# # ----------------- WS: AUDIO OUTPUT -----------------
# @app.websocket("/ws/receive_audio")
# async def receive_audio_ws(websocket: WebSocket):
#     await websocket.accept()
#     logger.info("Receive-audio WebSocket connected")
#     try:
#         response_sockets["default"] = websocket
#         while True:
#             msg = await websocket.receive_text()  # For keep-alive
#             logger.debug(f"Keep-alive message received: {msg}")
#     except WebSocketDisconnect:
#         logger.info("Receive-audio WebSocket disconnected")
#         response_sockets.pop("default", None)

# # ----------------- RUN SERVER -----------------
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)







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
import openai

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# --- Configuration ---
openai.api_key = "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"  # Add your OpenAI API Key here

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

def convert_to_mulaw(input_audio: bytes) -> bytes:
    """Convert audio to mu-law encoding using ffmpeg."""
    try:
        # Convert raw audio to mu-law using ffmpeg
        process = subprocess.Popen(
            [
                "ffmpeg", "-f", "s16le", "-ar", "16000", "-ac", "1", "-i", "pipe:0", "-f", "mulaw", "pipe:1"
            ],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        # Write audio to stdin
        out, err = process.communicate(input=input_audio)
        if process.returncode != 0:
            logger.error(f"Error during ffmpeg conversion: {err.decode()}")
            return None

        return out
    except Exception as e:
        logger.error(f"Error converting audio to mu-law: {e}")
        return None

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
                "Content-Type": "audio/mulaw;rate=8000"  # or audio/mulaw etc. depending on frontend format
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
                }
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

# ----------------- AUDIO TRANSCRIPTION WITH OPENAI -----------------
async def transcribe_audio_with_openai(audio: bytes) -> str:
    try:
        # Save the audio to a temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio)
            tmp.flush()

            # Use the old openai.Audio.transcribe method
            with open(tmp.name, "rb") as audio_file:
                transcript = openai.Audio.transcribe(
                    model="whisper-1",
                    file=audio_file
                )
                return transcript["text"]

    except Exception as e:
        logger.error(f"❌ Error during transcription: {e}")
        return None

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
