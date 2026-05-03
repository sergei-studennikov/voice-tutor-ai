import asyncio
import websockets
import json
import base64

async def test():
    uri = "ws://localhost:8000/ws"
    async with websockets.connect(uri) as websocket:
        # Create dummy audio data (or use your real base64 string)
        payload = json.dumps({
            "type": "audio",
            "data": "UklGRi9vAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YT1vAAA=" # Tiny silent WAV
        })
        
        await websocket.send(payload)
        print("Data sent, waiting for response...")
        
        try:
            # Wait up to 30 seconds for a response
            response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
            print("Response received:", response)
        except asyncio.TimeoutError:
            print("Timed out waiting for response.")

asyncio.run(test())
