"""
Cosmo Voice Assistant - Python Backend

Empfängt Audio vom ESP32 via aioesphomeapi voice_assistant,
transkribiert mit Whisper (VAD), antwortet mit Piper TTS.
"""
import asyncio
import io
import wave
import socket
import struct
from pathlib import Path
from aiohttp import web
from aioesphomeapi import APIClient, ReconnectLogic
from aioesphomeapi.model import VoiceAssistantAudioSettings
from piper import PiperVoice

# ============== KONFIGURATION ==============
ESP_IP = "192.168.178.82"
ESP_PORT = 6053
ESP_PASSWORD = ""

HTTP_PORT = 8080

# Audio Settings
SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2  # 16-bit = 2 bytes
CHANNELS = 1

# VAD Settings
SILENCE_THRESHOLD = 500  # RMS unter diesem Wert = Stille
SILENCE_DURATION_MS = 800  # ms Stille bevor Transkription startet
MIN_AUDIO_SECONDS = 0.5  # Mindestlänge für Transkription
MAX_AUDIO_SECONDS = 30  # Maximale Aufnahmelänge

# Piper TTS
MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "de_DE-thorsten-high.onnx"

# ============== GLOBALS ==============
whisper_model = None
voice = None
current_audio: bytes = b""
cli: APIClient = None
local_ip: str = ""
media_player_key: int = None

# Audio Buffer für aktive Aufnahme
audio_buffer = bytearray()
silence_chunks = 0
is_recording = False


def get_local_ip() -> str:
    """Ermittelt die lokale IP-Adresse"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
    finally:
        s.close()


def load_models():
    """Lädt TTS und STT Modelle"""
    global voice, whisper_model
    
    # Piper TTS
    print(f"🔊 Lade Piper TTS: {MODEL_PATH}")
    voice = PiperVoice.load(str(MODEL_PATH))
    print(f"✅ Piper bereit (Sample Rate: {voice.config.sample_rate})")
    
    # Whisper STT (lazy load beim ersten Aufruf)
    print("🎤 Whisper wird beim ersten Aufruf geladen...")


def detect_silence(audio_data: bytes) -> bool:
    """Erkennt ob die letzten Samples Stille sind"""
    samples_needed = int(SAMPLE_RATE * SILENCE_DURATION_MS / 1000) * SAMPLE_WIDTH
    if len(audio_data) < samples_needed:
        return False
    
    end_audio = audio_data[-samples_needed:]
    samples = struct.unpack(f'<{len(end_audio)//2}h', end_audio)
    rms = (sum(s**2 for s in samples) / len(samples)) ** 0.5
    return rms < SILENCE_THRESHOLD


def transcribe_audio(audio_data: bytes) -> str:
    """Transkribiert Audio mit Whisper"""
    global whisper_model
    
    try:
        import whisper
        import tempfile
        
        if whisper_model is None:
            print("🔄 Lade Whisper Modell (base)...")
            whisper_model = whisper.load_model("base")
            print("✅ Whisper bereit!")
        
        # WAV Datei erstellen
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            with wave.open(f, 'wb') as wav:
                wav.setframerate(SAMPLE_RATE)
                wav.setsampwidth(SAMPLE_WIDTH)
                wav.setnchannels(CHANNELS)
                wav.writeframes(audio_data)
            temp_path = f.name
        
        # Transkribieren
        result = whisper_model.transcribe(temp_path, language="de")
        Path(temp_path).unlink()
        
        text = result["text"].strip()
        print(f"📝 Whisper: '{text}'")
        return text
        
    except ImportError:
        print("⚠️ Whisper nicht installiert: pip install openai-whisper")
        return ""
    except Exception as e:
        print(f"❌ Whisper Fehler: {e}")
        return ""


def generate_tts_wav(text: str, target_rate: int = 16000) -> bytes:
    """Generiert WAV Audio mit Piper TTS"""
    print(f"🔊 TTS: '{text}'")
    
    # RAW Audio generieren
    raw_buffer = io.BytesIO()
    for chunk in voice.synthesize(text):
        raw_buffer.write(chunk.audio_int16_bytes)
    raw_data = raw_buffer.getvalue()
    
    # Resample wenn nötig
    source_rate = voice.config.sample_rate
    if source_rate != target_rate:
        samples = struct.unpack(f'<{len(raw_data)//2}h', raw_data)
        ratio = target_rate / source_rate
        new_length = int(len(samples) * ratio)
        resampled = [samples[min(int(i / ratio), len(samples)-1)] for i in range(new_length)]
        raw_data = struct.pack(f'<{len(resampled)}h', *resampled)
    
    # WAV erstellen
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav:
        wav.setframerate(target_rate)
        wav.setsampwidth(2)
        wav.setnchannels(1)
        wav.writeframes(raw_data)
    
    return wav_buffer.getvalue()


# ============== HTTP SERVER ==============
async def audio_handler(request):
    """HTTP Handler für TTS Audio"""
    if current_audio:
        return web.Response(
            body=current_audio,
            content_type='audio/wav',
            headers={'Content-Length': str(len(current_audio))}
        )
    return web.Response(status=404, text="No audio")


async def start_http_server():
    """Startet HTTP Server für TTS Audio"""
    app = web.Application()
    app.router.add_get('/audio.wav', audio_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', HTTP_PORT)
    await site.start()
    
    ip = get_local_ip()
    print(f"🌐 HTTP Server: http://{ip}:{HTTP_PORT}")
    return ip


# ============== VOICE ASSISTANT CALLBACKS ==============
async def handle_start(
    conversation_id: str,
    flags: int,
    audio_settings: VoiceAssistantAudioSettings,
    wake_word_phrase: str | None
) -> int | None:
    """Wird aufgerufen wenn ESP32 Audio senden will"""
    global audio_buffer, silence_chunks, is_recording
    
    print(f"\n🎤 Voice Assistant Start (Wake Word: {wake_word_phrase})")
    audio_buffer = bytearray()
    silence_chunks = 0
    is_recording = True
    
    # Kein UDP Server nötig - wir nutzen handle_audio
    # Rückgabe None = Audio kommt über API (handle_audio)
    return None


async def handle_stop(abort: bool):
    """Wird aufgerufen wenn ESP32 Audio-Stream beendet"""
    global is_recording, audio_buffer
    
    if abort:
        print("⚠️ Voice Assistant abgebrochen")
        is_recording = False
        audio_buffer = bytearray()
        return
    
    print(f"🛑 Voice Assistant Stop ({len(audio_buffer)/SAMPLE_RATE/SAMPLE_WIDTH:.1f}s Audio)")
    is_recording = False
    
    # Transkribieren wenn genug Audio
    if len(audio_buffer) >= MIN_AUDIO_SECONDS * SAMPLE_RATE * SAMPLE_WIDTH:
        await process_audio()
    else:
        print("⚠️ Zu wenig Audio für Transkription")


async def handle_audio(data: bytes):
    """Wird für jeden Audio-Chunk aufgerufen"""
    global audio_buffer, silence_chunks, is_recording
    
    if not is_recording:
        return
    
    audio_buffer.extend(data)
    
    # VAD: Stille erkennen
    min_bytes = int(MIN_AUDIO_SECONDS * SAMPLE_RATE * SAMPLE_WIDTH)
    max_bytes = int(MAX_AUDIO_SECONDS * SAMPLE_RATE * SAMPLE_WIDTH)
    
    if len(audio_buffer) > min_bytes:
        if detect_silence(bytes(audio_buffer)):
            silence_chunks += 1
            # ~10 chunks = SILENCE_DURATION_MS
            if silence_chunks >= 10:
                print(f"🔇 Stille erkannt - beende Aufnahme")
                is_recording = False
                await process_audio()
        else:
            silence_chunks = 0
    
    # Max Länge
    if len(audio_buffer) >= max_bytes:
        print(f"⏱️ Max Aufnahmezeit erreicht")
        is_recording = False
        await process_audio()


async def process_audio():
    """Verarbeitet aufgenommenes Audio"""
    global audio_buffer, current_audio
    
    audio_data = bytes(audio_buffer)
    audio_buffer = bytearray()
    
    duration = len(audio_data) / SAMPLE_RATE / SAMPLE_WIDTH
    print(f"📊 Verarbeite {duration:.1f}s Audio...")
    
    # Transkribieren
    text = transcribe_audio(audio_data)
    
    if text:
        # Hier könnte ein LLM antworten - für jetzt: Echo
        response = f"Du hast gesagt: {text}"
        await send_tts(response)
    else:
        await send_tts("Ich habe dich leider nicht verstanden.")


async def send_tts(text: str):
    """Sendet TTS Audio an ESP32"""
    global current_audio, cli, media_player_key, local_ip
    
    current_audio = generate_tts_wav(text, target_rate=16000)
    audio_url = f"http://{local_ip}:{HTTP_PORT}/audio.wav"
    
    print(f"🔈 Sende TTS: {audio_url}")
    
    try:
        cli.media_player_command(
            key=media_player_key,
            media_url=audio_url,
            announcement=True,
        )
        print("✅ Audio gesendet!")
    except Exception as e:
        print(f"❌ Fehler: {e}")


# ============== MAIN ==============
async def main():
    global cli, local_ip, media_player_key
    
    # Modelle laden
    load_models()
    
    # HTTP Server starten
    local_ip = await start_http_server()
    
    # ESPHome Client
    cli = APIClient(ESP_IP, ESP_PORT, ESP_PASSWORD)
    
    async def on_connect():
        global media_player_key
        print("✅ Verbunden mit Cosmo!")
        
        entities, services = await cli.list_entities_services()
        
        print("\n📋 Entities:")
        for e in entities:
            name = getattr(e, 'name', 'N/A')
            print(f"  - {type(e).__name__}: {name}")
            if 'Media Player' in name:
                media_player_key = e.key
                print(f"    → Media Player Key: {media_player_key}")
        
        # Voice Assistant abonnieren
        print("\n🎙️ Abonniere Voice Assistant...")
        cli.subscribe_voice_assistant(
            handle_start=handle_start,
            handle_stop=handle_stop,
            handle_audio=handle_audio,
        )
        
        print("\n👂 Bereit! Sage 'Okay Nabu' zum ESP32...")
    
    async def on_disconnect(expected):
        print("⚠️ Verbindung getrennt")
    
    async def on_error(err):
        print(f"❌ Fehler: {err}")
    
    reconnect = ReconnectLogic(
        client=cli,
        on_connect=on_connect,
        on_disconnect=on_disconnect,
        on_connect_error=on_error,
    )
    
    await reconnect.start()
    
    # Keep alive
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
