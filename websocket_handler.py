import asyncio
import base64
import json
import aiohttp
from services.deepgram import DEEPGRAM_WS_URL, get_deepgram_headers
from services.lyzr import query_lyzr
from services.elevenlabs import stream_to_elevenlabs

async def process_audio_stream(twilio_ws):
    stream_sid = None
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(DEEPGRAM_WS_URL, headers=get_deepgram_headers()) as dg_ws:

            async def forward_twilio():
                nonlocal stream_sid
                while True:
                    try:
                        data = await twilio_ws.receive_text()
                        message = json.loads(data)
                        event = message.get("event")

                        if event == "start":
                            stream_sid = message["start"]["streamSid"]
                            print(f"🔵 Twilio stream started: {stream_sid}")
                        elif event == "media":
                            chunk = base64.b64decode(message["media"]["payload"])
                            await dg_ws.send_bytes(chunk)
                        elif event == "stop":
                            print("⏹️ Twilio stream stopped")
                            await dg_ws.close()
                            break
                    except Exception as e:
                        print("❌ Error receiving from Twilio:", e)
                        break

            async def receive_from_deepgram():
                async for msg in dg_ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        if data.get("channel"):
                            transcript = data["channel"]["alternatives"][0].get("transcript", "")
                            if transcript:
                                print(f"📝 Got transcript: {transcript}")
                                lyzr_response = await query_lyzr(transcript)
                                if lyzr_response:
                                    print(f"🧠 Lyzr response: {lyzr_response}")
                                    await stream_to_elevenlabs(lyzr_response, twilio_ws, stream_sid)

            await asyncio.gather(forward_twilio(), receive_from_deepgram())
