# Home Assistant Voice Assistant - Docker Setup

## Starten

```bash
cd docker

# Mit Docker:
docker compose up -d

# Mit Podman:
podman-compose up -d
```

## Nach dem Start

1. **Home Assistant öffnen**: http://localhost:8123
2. **Erstkonfiguration** durchführen (Account erstellen)

## Integrationen hinzufügen

Nach der Erstkonfiguration:

### Wyoming Whisper (STT)
1. Einstellungen → Geräte & Dienste → Integration hinzufügen
2. Suche "Wyoming Protocol"
3. Host: `whisper` (oder `localhost` wenn network_mode: host)
4. Port: `10300`

### Wyoming Piper (TTS)
1. Integration hinzufügen → Wyoming Protocol
2. Host: `piper`
3. Port: `10200`

### Ollama (LLM)
1. Integration hinzufügen → Ollama
2. Host: `http://ollama:11434`
3. **Wichtig**: Erst ein Modell herunterladen:
   ```bash
   docker exec -it ollama ollama pull llama3.2:3b
   ```

## Sprachassistent einrichten

1. Einstellungen → Sprachassistenten
2. "Assistent hinzufügen"
3. Konfigurieren:
   - **Sprache**: Deutsch
   - **Konversationsagent**: Ollama (oder Home Assistant)
   - **Sprache-zu-Text**: Whisper
   - **Text-zu-Sprache**: Piper

## ESPHome verbinden

Dein ESP32 (`cosmo.yaml`) braucht nur:

```yaml
voice_assistant:
  microphone: cosmo_mic
  media_player: cosmo_media_player
```

Home Assistant erkennt ihn automatisch!

## Ordnerstruktur

Nach dem Start werden diese Ordner erstellt:
```
docker/
├── compose.yaml
├── homeassistant/config/    # HA Konfiguration
├── whisper/data/            # Whisper Modelle
├── piper/data/              # Piper Stimmen
└── ollama/data/             # LLM Modelle
```

## GPU für Ollama (optional)

Für schnellere LLM-Antworten, kommentiere in `compose.yaml` den `deploy` Block bei Ollama ein.

## Ports

| Service       | Port  | Beschreibung          |
|---------------|-------|-----------------------|
| Home Assistant| 8123  | Web UI                |
| Whisper       | 10300 | Wyoming STT           |
| Piper         | 10200 | Wyoming TTS           |
| Ollama        | 11434 | LLM API               |
| OpenWakeWord  | 10400 | Wake Word (optional)  |
