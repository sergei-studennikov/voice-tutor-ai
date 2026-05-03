import socket
import httpx
import asyncio

# The "Gateway" IP is usually the host machine from inside a Docker container
GATEWAY = "172.17.0.1" 

SERVICES = {
    "STT (Whisper)": {"host": GATEWAY, "port": 9000, "type": "http"},
    "LLM (Ollama)": {"host": GATEWAY, "port": 11434, "type": "http"},
    "TTS (Piper)": {"host": GATEWAY, "port": 10200, "type": "tcp"}
}

def test_tcp_socket(name, host, port):
    print(f"🔍 Testing TCP Socket for {name} ({host}:{port})...", end=" ")
    try:
        with socket.create_connection((host, port), timeout=3):
            print("✅ SUCCESS")
            return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False

async def test_http_service(name, url):
    print(f"🔍 Testing HTTP GET for {name} ({url})...", end=" ")
    try:
        async with httpx.AsyncClient() as client:
            # We just check if the port is listening, not a full request
            resp = await client.get(url, timeout=3)
            print(f"✅ SUCCESS (Status: {resp.status_code})")
    except httpx.ConnectError:
        print("❌ FAILED: Connection Refused")
    except Exception as e:
        # Some services return 404 or 401 on root, which still means connectivity is OK
        print(f"✅ OK (Received response: {type(e).__name__})")

async def main():
    print("--- DOCKER INTERNAL CONNECTIVITY TEST ---")
    
    # 1. Check TCP level first
    for name, config in SERVICES.items():
        test_tcp_socket(name, config['host'], config['port'])
    
    print("\n--- HTTP LEVEL TEST ---")
    # 2. Check HTTP specific paths
    await test_http_service("STT", f"http://{GATEWAY}:9000/")
    await test_http_service("Ollama", f"http://{GATEWAY}:11434/")

if __name__ == "__main__":
    asyncio.run(main())
