# Cosmo

Ein Offline-KI-Assistent basierend auf der Xiaozhi (ESP32-S3-BOX-3) Hardware.

## Entwicklung

Dieses Projekt nutzt `uv` für das Paketmanagement.

### Installation

```bash
uv sync
```

### Konfiguration

Erstelle eine `secrets.yaml` im `esphome` Ordner (falls nicht vorhanden) und trage deine WLAN-Zugangsdaten ein:

```yaml
wifi_ssid: "Dein WLAN Name"
wifi_password: "Dein WLAN Passwort"
```

### Flashen

Verbinde das ESP32-S3-BOX-3 Gerät per USB mit deinem Computer und führe folgenden Befehl aus:

```bash
uv run esphome run esphome/cosmo.yaml
```

Folge den Anweisungen im Terminal, um das Gerät auszuwählen und den Flash-Vorgang zu starten.

