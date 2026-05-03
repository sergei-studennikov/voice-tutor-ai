import asyncio
import base64
import json
import httpx
import io
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from wyoming.client import AsyncTcpClient
from wyoming.tts import Synthesize
from wyoming.audio import AudioChunk

app = FastAPI()

# --- CONFIG (Verified Gateway & Ports) ---
GATEWAY = "172.17.0.1" 
STT_URL = f"http://{GATEWAY}:9000/v1/audio/transcriptions"
OLLAMA_URL = f"http://{GATEWAY}:11434/api/generate"
TTS_HOST = GATEWAY
TTS_PORT = 10200
LLM_MODEL = "llama3.1:8b-instruct-q4_K_M"

async def tts_worker(text, websocket: WebSocket):
    """Verified Wyoming logic for Piper"""
    print(f"!!! DEBUG: STARTING TTS FOR: {text[:30]}... !!!", flush=True)
    client = AsyncTcpClient(TTS_HOST, TTS_PORT)
    try:
        async with client:
            await client.write_event(Synthesize(text=text).event())
            chunk_count = 0
            while True:
                event = await client.read_event()
                if event is None:
                    break
                
                if event.type == "audio-chunk":
                    chunk = AudioChunk.from_event(event)
                    await websocket.send_json({
                        "type": "audio_chunk",
                        "audio": base64.b64encode(chunk.audio).decode('utf-8')
                    })
                    chunk_count += 1
                elif event.type == "audio-stop":
                    print(f"!!! DEBUG: TTS STOPPED. SENT {chunk_count} CHUNKS !!!", flush=True)
                    break
    except Exception as e:
        print(f"!!! DEBUG: TTS WORKER CRASH: {e} !!!", flush=True)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("!!! DEBUG: WS ACCEPTED !!!", flush=True)
    
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            if msg.get("type") == "audio":
                print("!!! DEBUG: PROCESSING AUDIO REQUEST !!!", flush=True)
                
                # 1. STT Phase
                audio_bytes = base64.b64decode(msg.get("data"))
                audio_file = io.BytesIO(audio_bytes)
                user_text = ""
                
                async with httpx.AsyncClient() as client:
                    files = {'file': ('audio.wav', audio_file, 'audio/wav')}
                    stt_res = await client.post(STT_URL, files=files, data={'model': 'base.en'}, timeout=30.0)
                    
                    if stt_res.status_code == 200:
                        user_text = stt_res.json().get("text", "").strip()
                        print(f"!!! DEBUG: TRANSCRIBED: {user_text} !!!", flush=True)
                    else:
                        print(f"!!! DEBUG: STT ERROR {stt_res.status_code} !!!", flush=True)
                        continue

                if not user_text:
                    continue

                # 2. LLM Phase
                print("!!! DEBUG: CALLING OLLAMA !!!", flush=True)
                llm_text = ""
                async with httpx.AsyncClient() as client:
                    # Tutor Persona Prompt
                    tutor_prompt = (
                        f"You are a friendly English Tutor. Respond to the student: '{user_text}'. "
                        "Keep it under 3 sentences. Correct any grammar mistakes they made."
                    )
                    
                    llm_res = await client.post(OLLAMA_URL, json={
                        "model": LLM_MODEL,
                        "prompt": tutor_prompt,
                        "stream": False
                    }, timeout=120.0)
                    
                    if llm_res.status_code == 200:
                        llm_text = llm_res.json().get("response", "").strip()
                        print(f"!!! DEBUG: TUTOR SAYS: {llm_text} !!!", flush=True)
                    else:
                        print(f"!!! DEBUG: LLM ERROR {llm_res.status_code} !!!", flush=True)
                        continue

                # 3. TTS Phase
                if llm_text:
                    await tts_worker(llm_text, websocket)
                
                # 4. Final Signal
                await websocket.send_json({"type": "stream_end"})
                print("!!! DEBUG: INTERACTION COMPLETE !!!", flush=True)

    except WebSocketDisconnect:
        print("!!! DEBUG: DISCONNECT !!!", flush=True)
    except Exception as e:
        print(f"!!! DEBUG: GLOBAL CRASH: {str(e)} !!!", flush=True)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
