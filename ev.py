import asyncio
import json
import base64
import websockets

async def send_to_elevenlabs_via_ws(text: str, voice_id: str, api_key: str):
    uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input"

    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    # Format for WebSocket headers
    extra_headers = [(key, value) for key, value in headers.items()]

    # Payload to send to ElevenLabs
    payload = {
        "text": text,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.8
        }
    }

    try:
        async with websockets.connect(uri, extra_headers=extra_headers) as websocket:
            print(f"Connected to ElevenLabs WebSocket\nSending: {text}")

            await websocket.send(json.dumps(payload))

            while True:
                response = await websocket.recv()
                data = json.loads(response)

                print(f"Response: {json.dumps(data, indent=2)}")

                if data.get("audio"):
                    # Base64 decode audio
                    audio_bytes = base64.b64decode(data["audio"])
                    with open("output.mp3", "ab") as f:
                        f.write(audio_bytes)
                        print("Audio chunk saved.")
                
                if data.get("isFinal", False):
                    print("Final response received. Closing connection.")
                    break

    except Exception as e:
        print(f"Error during ElevenLabs WebSocket communication: {e}")



# Example usage
voice_id = "VR6AewLTigWG4xSOukaG"
api_key = "sk_e240470042f862f45d40083ef40fb5b7a8fba53e1295bdd8"
text = "Hello."
asyncio.run(send_to_elevenlabs_via_ws(text, voice_id, api_key))

