import asyncio
import httpx
import json
import wave
import os
import re
from wyoming.client import AsyncTcpClient
from wyoming.tts import Synthesize
from wyoming.audio import AudioChunk

# Internal Docker Config
STT_URL = "http://stt:8000/v1/audio/transcriptions"
OLLAMA_URL = "http://ollama:11434/api/generate"
TTS_HOST = "tts"
TTS_PORT = 10200
LLM_MODEL = "llama3.1:8b-instruct-q4_K_M"

INPUT_FILE = "/app/test_input.wav"
OUTPUT_FILE = "/app/test_output.wav"

async def synthesize_sentence(text):
    """Handshake with Piper for a single sentence."""
    audio = bytearray()
    client = AsyncTcpClient(TTS_HOST, TTS_PORT)
    try:
        async with client:
            await client.write_event(Synthesize(text=text).event())
            while True:
                event = await client.read_event()
                if event is None or event.type == "audio-stop":
                    break
                if event.type == "audio-chunk":
                    audio.extend(AudioChunk.from_event(event).audio)
        return audio
    except Exception as e:
        print(f"\n[TTS Error] {e}")
        return b""

async def run_pipeline():
    print(f"--- STARTING STREAMING 3-SENTENCE PIPELINE ---")
    
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Error: {INPUT_FILE} not found.")
        return

    # 1. PHASE: STT
    async with httpx.AsyncClient() as client:
        with open(INPUT_FILE, "rb") as f:
            res = await client.post(STT_URL, files={'file': f}, data={'model': 'base.en'}, timeout=60.0)
            user_text = res.json().get("text", "").strip()
    
    print(f"Transcribed: '{user_text}'")

    # 2. & 3. PHASE: LLM Stream + TTS Synthesis
    print(f"LLM Generating (3 sentences)...")
    final_audio = bytearray()
    sentence_buffer = ""
    sentence_count = 0

    prompt = (
        f"Context: {user_text}\n\n"
        "Task: Respond to the context. "
        "Rule: You MUST use exactly three sentences. No more, no less."
    )

    async with httpx.AsyncClient() as client:
        async with client.stream("POST", OLLAMA_URL, json={"model": LLM_MODEL, "prompt": prompt, "stream": True}, timeout=120.0) as response:
            async for line in response.aiter_lines():
                if not line: continue
                
                chunk = json.loads(line)
                token = chunk.get("response", "")
                sentence_buffer += token
                print(token, end="", flush=True)

                # Split at sentence boundaries (., !, ?)
                if any(p in token for p in [".", "!", "?"]) and sentence_count < 3:
                    # Extract the complete sentence
                    sentences = re.split(r'(?<=[.!?]) +', sentence_buffer.strip())
                    if len(sentences) > 1 or (chunk.get("done") and sentences):
                        to_process = sentences[0]
                        print(f"\n[Streaming to TTS]: {to_process}")
                        audio_chunk = await synthesize_sentence(to_process)
                        final_audio.extend(audio_chunk)
                        
                        # Keep the remainder in buffer
                        sentence_buffer = " ".join(sentences[1:])
                        sentence_count += 1

    # 4. Save result
    if final_audio:
        with wave.open(OUTPUT_FILE, "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(22050)
            f.writeframes(final_audio)
        print(f"\n\n✅ SUCCESS: Full streamed output saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(run_pipeline())
