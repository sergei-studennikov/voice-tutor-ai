import asyncio
import websockets
import json
import base64
import wave

async def test_and_save():
    uri = "ws://localhost:8000/ws"
    input_audio = "test_input.wav" 
    output_audio = "test_output.wav"
    audio_buffer = bytearray()

    try:
        # Load the question
        with open(input_audio, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode('utf-8')

        async with websockets.connect(uri) as websocket:
            print("🚀 Connection opened. Sending audio...")
            await websocket.send(json.dumps({
                "type": "audio", 
                "data": audio_base64
            }))
            
            print("📥 Waiting for Tutor's voice...")
            while True:
                response = await websocket.recv()
                msg = json.loads(response)
                
                if msg.get("type") == "audio_chunk":
                    # Decode and add to our buffer
                    chunk = base64.b64decode(msg["audio"])
                    audio_buffer.extend(chunk)
                    print(f"✅ Received: {len(chunk)} bytes", end="\r")
                
                if msg.get("type") == "stream_end":
                    print("\n🏁 Finished receiving audio.")
                    break

        # Save to file
        if audio_buffer:
            with wave.open(output_audio, "wb") as wav_file:
                wav_file.setnchannels(1)       # Mono
                wav_file.setsampwidth(2)      # 16-bit
                wav_file.setframerate(22050)  # Piper standard
                wav_file.writeframes(audio_buffer)
            print(f"💾 Success! Listen to: {output_audio}")
        else:
            print("⚠️ Error: No audio data was received.")

    except Exception as e:
        print(f"❌ Client Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_and_save())
