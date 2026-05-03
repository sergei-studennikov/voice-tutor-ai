import asyncio
import websockets
import json
import base64

async def test_with_real_audio():
    uri = "ws://localhost:8000/ws"
    # PATH TO YOUR REAL TEST FILE
    audio_file_path = "test_input.wav" 

    try:
        with open(audio_file_path, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode('utf-8')

        async with websockets.connect(uri) as websocket:
            print("🚀 WS Accepted. Sending real audio...")
            payload = json.dumps({
                "type": "audio", 
                "data": audio_base64
            })
            
            await websocket.send(payload)
            
            while True:
                response = await websocket.recv()
                msg = json.loads(response)
                print(f"📡 Server says: {msg}")
                if msg.get("type") == "stream_end":
                    break

    except Exception as e:
        print(f"❌ Client Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_with_real_audio())
