import asyncio
import io
import wave
import socket
from pathlib import Path
from aiohttp import web
from aioesphomeapi import APIClient, ReconnectLogic
from piper import PiperVoice

ESP_IP = "192.168.178.82"  # Deine ESP32 IP
ESP_PORT = 6053
ESP_PASSWORD = ""

# HTTP Server Port
HTTP_PORT = 8080

# Piper TTS Einstellungen
MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "de_DE-thorsten-high.onnx"

# Piper Voice laden (einmal beim Start)
print(f"🔊 Lade Piper TTS Modell: {MODEL_PATH}")
voice = PiperVoice.load(str(MODEL_PATH))
SAMPLE_RATE = voice.config.sample_rate  # 22050 für thorsten-high
print(f"✅ Piper TTS bereit! Sample Rate: {SAMPLE_RATE}")

# Aktuelles Audio für HTTP Server
current_audio: bytes = b""


def get_local_ip() -> str:
    """Ermittelt die lokale IP-Adresse"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


def generate_tts_wav(text: str, target_rate: int = 16000) -> bytes:
    """Generiert WAV Audio mit Piper TTS, optional resampled"""
    print(f"🔊 Generiere TTS: '{text}'")
    
    # Erst RAW Audio generieren
    raw_buffer = io.BytesIO()
    for chunk in voice.synthesize(text):
        raw_buffer.write(chunk.audio_int16_bytes)
    raw_data = raw_buffer.getvalue()
    
    # Resample wenn nötig
    if SAMPLE_RATE != target_rate:
        import struct
        samples = struct.unpack(f'<{len(raw_data)//2}h', raw_data)
        ratio = target_rate / SAMPLE_RATE
        new_length = int(len(samples) * ratio)
        resampled = []
        for i in range(new_length):
            src_idx = int(i / ratio)
            if src_idx < len(samples):
                resampled.append(samples[src_idx])
        raw_data = struct.pack(f'<{len(resampled)}h', *resampled)
        print(f"  Resampled: {SAMPLE_RATE} → {target_rate} Hz")
    
    # WAV erstellen
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setframerate(target_rate)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setnchannels(1)  # Mono
        wav_file.writeframes(raw_data)
    
    wav_data = wav_buffer.getvalue()
    print(f"✅ WAV generiert: {len(wav_data)} bytes")
    return wav_data


async def audio_handler(request):
    """HTTP Handler für Audio"""
    global current_audio
    if current_audio:
        return web.Response(
            body=current_audio,
            content_type='audio/wav',
            headers={'Content-Length': str(len(current_audio))}
        )
    return web.Response(status=404, text="No audio")


async def start_http_server():
    """Startet HTTP Server"""
    app = web.Application()
    app.router.add_get('/audio.wav', audio_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', HTTP_PORT)
    await site.start()
    
    local_ip = get_local_ip()
    print(f"🌐 HTTP Server: http://{local_ip}:{HTTP_PORT}")
    return local_ip


# Globale Variablen
wake_word_sensor_key = None
media_player_key = None
cli = None
local_ip = None


async def send_tts_to_speaker(text: str):
    """Generiert TTS und sendet URL an Media Player"""
    global cli, current_audio, local_ip, media_player_key
    
    # TTS als WAV generieren (16kHz für ESP32)
    current_audio = generate_tts_wav(text, target_rate=16000)
    
    # Audio URL
    audio_url = f"http://{local_ip}:{HTTP_PORT}/audio.wav"
    print(f"🔈 Sende Audio URL an Media Player: {audio_url}")
    
    try:
        # Media Player Befehl senden - announcement=True weil nur announcement_pipeline konfiguriert
        cli.media_player_command(
            key=media_player_key,
            media_url=audio_url,
            announcement=True,
        )
        print("✅ Media Player gestartet!")
    except Exception as e:
        print(f"❌ Fehler: {e}")


async def main():
    global wake_word_sensor_key, media_player_key, cli, local_ip
    
    # HTTP Server starten
    local_ip = await start_http_server()
    
    cli = APIClient(ESP_IP, ESP_PORT, ESP_PASSWORD)
    
    async def on_connect():
        global wake_word_sensor_key, media_player_key
        print("✅ Verbindung zu Cosmo steht!")
        
        # Entities und Services abrufen
        entities, services = await cli.list_entities_services()
        
        print("\n📋 Entities:")
        for e in entities:
            e_name = getattr(e, 'name', 'N/A')
            e_type = type(e).__name__
            print(f"  - {e_type}: {e_name} (key={e.key})")
            if 'Wake Word' in e_name:
                wake_word_sensor_key = e.key
            if 'Media Player' in e_name:
                media_player_key = e.key
                print(f"    ☝️ Media Player gefunden!")
        
        print("\n📋 Services:")
        for s in services:
            print(f"  - {s.name} (key={s.key})")
        
        async def handle_wake_word():
            print("\n🎤 Wake Word erkannt!")
            await send_tts_to_speaker("Hallo! Ich bin Cosmo.")
        
        def on_state_change(state):
            if wake_word_sensor_key and hasattr(state, 'key') and state.key == wake_word_sensor_key:
                if hasattr(state, 'state') and state.state:
                    asyncio.create_task(handle_wake_word())
        
        cli.subscribe_states(on_state_change)
        print("\n👂 Warte auf Wake Word 'Okay Nabu'...")
    
    async def on_disconnect(expected_disconnect):
        print("⚠️ Verbindung getrennt...")
    
    async def on_connect_error(err):
        print(f"❌ Fehler: {err}")
    
    reconnect = ReconnectLogic(
        client=cli,
        on_connect=on_connect,
        on_disconnect=on_disconnect,
        on_connect_error=on_connect_error,
    )
    
    await reconnect.start()
    
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
