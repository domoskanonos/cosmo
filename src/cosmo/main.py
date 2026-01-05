import asyncio
import io
from pathlib import Path
from aioesphomeapi import APIClient, ReconnectLogic, VoiceAssistantEventType
from piper import PiperVoice

ESP_IP = "192.168.178.82"  # Deine ESP32 IP
ESP_PORT = 6053
ESP_PASSWORD = ""

# Piper TTS Einstellungen
MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "de_DE-thorsten-high.onnx"

# Piper Voice laden (einmal beim Start)
print(f"🔊 Lade Piper TTS Modell: {MODEL_PATH}")
voice = PiperVoice.load(str(MODEL_PATH))
SAMPLE_RATE = voice.config.sample_rate  # 22050 für thorsten-high
print(f"✅ Piper TTS bereit! Sample Rate: {SAMPLE_RATE}")


def generate_tts_raw(text: str) -> bytes:
    """Generiert RAW PCM Audio mit Piper TTS (16-bit, mono)"""
    print(f"🔊 Generiere TTS: '{text}'")
    
    audio_buffer = io.BytesIO()
    
    # synthesize() gibt AudioChunk Objekte zurück
    for chunk in voice.synthesize(text):
        audio_buffer.write(chunk.audio_int16_bytes)
    
    raw_data = audio_buffer.getvalue()
    print(f"✅ RAW Audio generiert: {len(raw_data)} bytes ({len(raw_data) // 2} samples)")
    return raw_data


def resample_audio(audio: bytes, from_rate: int, to_rate: int) -> bytes:
    """Einfaches Resampling durch Wiederholung/Überspringen von Samples"""
    import struct
    
    # 16-bit samples
    samples = struct.unpack(f'<{len(audio)//2}h', audio)
    
    ratio = to_rate / from_rate
    new_length = int(len(samples) * ratio)
    
    resampled = []
    for i in range(new_length):
        src_idx = int(i / ratio)
        if src_idx < len(samples):
            resampled.append(samples[src_idx])
    
    return struct.pack(f'<{len(resampled)}h', *resampled)


# Globale Variablen
wake_word_sensor_key = None
cli = None
voice_assistant_started = False


async def handle_voice_assistant_start(conversation_id: str, flags: int, audio_settings: dict, wake_word_phrase: str | None):
    """Callback wenn Voice Assistant gestartet wird"""
    global voice_assistant_started
    print(f"🎙️ Voice Assistant gestartet! conversation_id={conversation_id}")
    voice_assistant_started = True


async def handle_voice_assistant_stop():
    """Callback wenn Voice Assistant gestoppt wird"""
    global voice_assistant_started
    print("🛑 Voice Assistant gestoppt")
    voice_assistant_started = False


async def send_tts_to_speaker(text: str):
    """Sendet TTS Audio zum ESP32 Speaker"""
    global cli
    
    # TTS generieren (22050 Hz)
    raw_audio = generate_tts_raw(text)
    
    # Resample zu 16000 Hz (ESP32 Speaker Rate)
    print("🔄 Resample von 22050 Hz auf 16000 Hz...")
    resampled_audio = resample_audio(raw_audio, 22050, 16000)
    print(f"✅ Resampled: {len(resampled_audio)} bytes")
    
    print(f"🔈 Sende TTS Audio zum ESP32...")
    
    try:
        # TTS Stream Start Event
        cli.send_voice_assistant_event(
            event_type=VoiceAssistantEventType.VOICE_ASSISTANT_TTS_STREAM_START,
            data={}
        )
        print("  → TTS_STREAM_START")
        
        await asyncio.sleep(0.1)
        
        # Audio in Chunks senden
        CHUNK_SIZE = 1024  # 512 samples bei 16-bit
        chunks_sent = 0
        for i in range(0, len(resampled_audio), CHUNK_SIZE):
            chunk = resampled_audio[i:i + CHUNK_SIZE]
            cli.send_voice_assistant_audio(chunk)
            chunks_sent += 1
            await asyncio.sleep(0.03)  # ~32ms pro Chunk bei 16kHz
        
        print(f"  → {chunks_sent} Chunks gesendet ({len(resampled_audio)} bytes)")
        
        await asyncio.sleep(0.5)
        
        # TTS Stream End Event
        cli.send_voice_assistant_event(
            event_type=VoiceAssistantEventType.VOICE_ASSISTANT_TTS_STREAM_END,
            data={}
        )
        print("  → TTS_STREAM_END")
        print("✅ TTS gesendet!")
        
    except Exception as e:
        print(f"❌ Fehler: {e}")


async def main():
    global wake_word_sensor_key, cli
    
    cli = APIClient(ESP_IP, ESP_PORT, ESP_PASSWORD)
    
    async def on_connect():
        global wake_word_sensor_key
        print("✅ Verbindung zu Cosmo steht!")
        
        # Entities abrufen
        entities, services = await cli.list_entities_services()
        
        print("\n📋 Verfügbare Entities:")
        for e in entities:
            e_name = getattr(e, 'name', 'N/A')
            e_type = type(e).__name__
            print(f"  - {e_type}: key={e.key}, name={e_name}")
            
            if 'Wake Word' in e_name:
                wake_word_sensor_key = e.key
                print(f"    ☝️ Wake Word Sensor!")
        
        # Services anzeigen
        print("\n📋 Verfügbare Services:")
        for s in services:
            print(f"  - {s.name}")
        
        # Voice Assistant subscriben
        try:
            async def va_handle_start(conversation_id: str, flags: int, audio_settings, wake_word_phrase: str | None):
                print(f"🎙️ Voice Assistant Start: {conversation_id}")
                return 0  # port (nicht verwendet)
            
            async def va_handle_stop(abort: bool):
                print(f"🛑 Voice Assistant Stop (abort={abort})")
            
            stop_callback = cli.subscribe_voice_assistant(
                handle_start=va_handle_start,
                handle_stop=va_handle_stop,
            )
            print("\n✅ Voice Assistant subscribed!")
        except Exception as e:
            print(f"\n⚠️ Voice Assistant subscribe fehlgeschlagen: {e}")
        
        async def handle_wake_word():
            print("\n🎤 Wake Word erkannt!")
            await send_tts_to_speaker("Hallo! Ich bin Cosmo.")
        
        def on_state_change(state):
            if wake_word_sensor_key and hasattr(state, 'key') and state.key == wake_word_sensor_key:
                if hasattr(state, 'state') and state.state:
                    print(f"📡 Wake Word!")
                    asyncio.create_task(handle_wake_word())
        
        cli.subscribe_states(on_state_change)
        print("\n👂 Warte auf Wake Word 'Okay Nabu'...")
    
    async def on_disconnect(expected_disconnect):
        print("⚠️ Verbindung getrennt...")
    
    async def on_connect_error(err):
        print(f"❌ Verbindungsfehler: {err}")
    
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
