# Cosmo Wakeword Service

This service runs the openWakeWord detection for Cosmo.

## Setup

### Local Development (using uv)

1. Navigate to this directory:
   ```bash
   cd wakeword
   ```

2. Initialize/Sync dependencies:
   ```bash
   uv sync
   ```

3. Run the service:
   ```bash
   uv run main.py
   ```

   Arguments:
   - `--model <name>`: Specify model (default: "alexa")
   - `--debug`: Enable debug output

### Docker

1. Build the image:
   ```bash
   docker build -t cosmo-wakeword .
   ```

2. Run the container:
   Note: You need to pass the audio device to the container. This is system specific.
   For Linux/ALSA:
   ```bash
   docker run --device /dev/snd cosmo-wakeword
   ```
   For Windows/Mac, accessing the microphone from Docker can be tricky and might require specific setup or might not work reliably depending on the backend.

## Environment Variables

- `SELECTED_MIC`: ID of the microphone to use (integer). If not set, the service will prompt or use default.
- `DIST_FOLDER`: Folder to write detection logs to.
