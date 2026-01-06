# Cosmo

Ein Offline-KI-Assistent basierend auf der Xiaozhi (ESP32-S3-BOX-3) Hardware mit Home Assistant Integration.

## Architektur

```
┌─────────────────┐     WiFi      ┌─────────────────────────────────┐
│   ESP32-S3      │◄────────────► │         Docker Stack            │
│                 │               │                                 │
│ • micro_wake_word               │ • Home Assistant (Port 8123)    │
│ • Audio Streaming               │ • Whisper STT    (Port 10300)   │
│ • Media Player  │               │ • Piper TTS      (Port 10200)   │
│                 │               │ • Ollama LLM     (Port 11434)   │
└─────────────────┘               └─────────────────────────────────┘
```

## Voraussetzungen

- [uv](https://github.com/astral-sh/uv) - Python Paketmanager
- [Docker](https://docs.docker.com/get-docker/) oder [Podman](https://podman.io/)

## Installation

### 1. Python Dependencies

```bash
uv sync
```

### 2. ESPHome Secrets

Erstelle `esphome/secrets.yaml`:

```yaml
wifi_ssid: "Dein WLAN Name"
wifi_password: "Dein WLAN Passwort"
```

### 3. ESP32 Flashen

```bash
# Über USB:
uv run esphome run esphome/cosmo.yaml

# Über Netzwerk (OTA):
uv run esphome run esphome/cosmo.yaml --device 192.168.178.82
```

## Home Assistant Stack starten

### Mit Docker:

```bash
cd docker
docker compose up -d
```

### Mit Podman:

```bash
cd docker

# Option 1: podman-compose (muss installiert sein)
pip install podman-compose
podman-compose up -d

# Option 2: podman mit docker-compose Kompatibilität
podman compose up -d
```

### Logs anzeigen:

```bash
# Docker:
docker compose logs -f

# Podman:
podman-compose logs -f
```

### Stoppen:

```bash
# Docker:
docker compose down

# Podman:
podman-compose down
```

## Home Assistant einrichten

1. **Öffne**: http://localhost:8123
2. **Account erstellen** (Erstkonfiguration)

### Integrationen hinzufügen

Gehe zu **Einstellungen → Geräte & Dienste → Integration hinzufügen**:

| Integration      | Host        | Port  |
|------------------|-------------|-------|
| Wyoming Protocol | `localhost` | 10300 | (Whisper STT)
| Wyoming Protocol | `localhost` | 10200 | (Piper TTS)
| Ollama           | `http://localhost:11434` | - |

### Ollama Modell laden

```bash
# Docker:
docker exec -it ollama ollama pull llama3.2:3b

# Podman:
podman exec -it ollama ollama pull llama3.2:3b
```

### Sprachassistent konfigurieren

1. **Einstellungen → Sprachassistenten → Assistent hinzufügen**
2. Konfigurieren:
   - Sprache: **Deutsch**
   - Konversationsagent: **Ollama** (oder Home Assistant)
   - Sprache-zu-Text: **whisper**
   - Text-zu-Sprache: **piper**

### ESPHome Gerät hinzufügen

1. **Einstellungen → Geräte & Dienste → ESPHome**
2. Host: `192.168.178.82` (IP deines ESP32)
3. Das Gerät wird automatisch erkannt

### Updates einspielen

Wenn Sie Änderungen an der Konfiguration vorgenommen haben (oder `git pull` ausgeführt haben), flashen Sie das Gerät erneut mit dem gleichen Befehl:

```bash
uv run esphome run esphome/cosmo.yaml
```

## Ordnerstruktur

```
cosmo/
├── esphome/
│   ├── cosmo.yaml        # Haupt-Konfiguration (Entry Point)
│   ├── secrets.yaml      # WLAN Credentials
│   └── packages/         # Modularisierte Konfiguration
│       ├── network.yaml
│       ├── hardware.yaml
│       ├── audio.yaml
│       ├── voice.yaml
│       └── display.yaml
├── docker/
│   ├── compose.yaml      # Docker/Podman Stack
│   ├── homeassistant/    # HA Config (wird erstellt)
│   ├── whisper/          # Whisper Modelle
│   ├── piper/            # Piper Stimmen
│   └── ollama/           # LLM Modelle
└── src/cosmo/            # Python Scripts (optional)
```

## Ports

| Service        | Port  | Beschreibung     |
|----------------|-------|------------------|
| Home Assistant | 8123  | Web UI           |
| Whisper        | 10300 | Wyoming STT      |
| Piper          | 10200 | Wyoming TTS      |
| Ollama         | 11434 | LLM API          |
| ESPHome API    | 6053  | Native API       |

## Troubleshooting

### ESP32 verbindet nicht
```bash
# Logs anschauen:
uv run esphome logs esphome/cosmo.yaml --device 192.168.178.82
```

### Home Assistant findet ESP32 nicht
- Prüfe ob `network_mode: host` in compose.yaml aktiv ist
- ESP32 und Server müssen im gleichen Netzwerk sein

### Ollama zu langsam
- GPU Support aktivieren (siehe compose.yaml)
- Kleineres Modell nutzen: `ollama pull llama3.2:1b`

