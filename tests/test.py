import asyncio
import wave
from wyoming.client import AsyncTcpClient
from wyoming.tts import Synthesize
from wyoming.audio import AudioChunk, AudioStop

# Configuration
HOST = "127.0.0.1"
PORT = 10200
OUTPUT_FILE = "output.wav"

async def main():
    print(f"Connecting to Piper via TCP at {HOST}:{PORT}...")
    
    client = AsyncTcpClient(HOST, PORT)
    audio_data = bytearray()

    try:
        async with client:
            print("Connected. Sending synthesis request...")
            # Use .event() to get the actual Event object for writing
            await client.write_event(Synthesize(text="Let's start our dayly english language training!").event())

            while True:
                event = await client.read_event()
                if event is None:
                    break

                # Use the raw event type string from your hex logs
                if event.type == "audio-chunk":
                    # AudioChunk.from_event might still work, 
                    # but if it fails, event.payload contains the raw bytes.
                    chunk = AudioChunk.from_event(event)
                    audio_data.extend(chunk.audio)
                
                elif event.type == "audio-stop":
                    print("Received audio-stop signal.")
                    break
                
                elif event.type == "error":
                    print(f"Server Error: {event.data}")
                    break

        if audio_data:
            with wave.open(OUTPUT_FILE, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(22050)
                wav_file.writeframes(audio_data)
            print(f"--- SUCCESS ---")
            print(f"File saved to {OUTPUT_FILE} ({len(audio_data)} bytes)")
        else:
            print("No audio data captured.")

    except Exception as e:
        print(f"Communication error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
