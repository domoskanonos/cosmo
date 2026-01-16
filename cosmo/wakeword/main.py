import openwakeword
from openwakeword.model import Model
import numpy as np
import sounddevice as sd
import logging
import threading
import time
import sys
import os
import argparse
from datetime import datetime
from typing import Optional, Callable
from dotenv import load_dotenv

load_dotenv()

try:
    from select_mic import get_microphone
except ImportError:
    def get_microphone():
        print("Module 'select_mic' not found. Using default device.")
        return None

# Configure logging if not already configured
logger = logging.getLogger(__name__)

class WakeWordListener:
    def __init__(self, 
                 model_path: str = "alexa", 
                 device_id: Optional[int] = None, 
                 chunk_size: int = 1280,
                 on_wake_word: Optional[Callable[[str, float], None]] = None,
                 debug: bool = False):
        """
        Initialize the WakeWordListener.
        
        Args:
            model_path: Name of the model to use (default: alexa)
            device_id: Audio input device ID
            chunk_size: Audio chunk size
            on_wake_word: Callback function to receive wake word events (model_name, score)
            debug: Enable debug logging/output
        """
        self.model_path = model_path
        self.device_id = device_id
        self.chunk_size = chunk_size
        self.on_wake_word = on_wake_word
        self.debug = debug
        self.running = False
        self.thread = None
        
        # Initialize resources
        logger.info(f"Loading openwakeword model: {model_path}")
        openwakeword.utils.download_models()
        self.oww_model = Model(wakeword_models=[model_path], inference_framework="onnx")
        logger.debug("Model loaded successfully")

    def _audio_callback(self, indata, frames, time, status):
        if status:
            logger.warning(f"Audio status: {status}")
            
        # Convert audio to numpy array (flat int16)
        audio_data = indata.flatten()
        
        # Calculate volume for debug visualization
        if self.debug:
            volume_norm = float(np.linalg.norm(audio_data) / 500)
        
        # Get predictions
        prediction = self.oww_model.predict(audio_data)
        
        # Process predictions
        for mdl in self.oww_model.prediction_buffer.keys():
            scores = list(self.oww_model.prediction_buffer[mdl])
            curr_score = scores[-1]
            
            # Debug output
            if self.debug and curr_score > 0.01:
                logger.debug(f"Score for {mdl}: {curr_score:.3f} (Vol: {volume_norm:.1f})")
            
            # Wake word detected
            if curr_score > 0.5:
                logger.info(f"Wake word detected: {mdl} (Score: {curr_score:.2f})")
                
                # Reset buffer to avoid multiple triggers
                self.oww_model.prediction_buffer[mdl] = list(np.zeros(len(scores)))
                
                # Call the external callback if registered
                if self.on_wake_word:
                    try:
                        self.on_wake_word(mdl, curr_score)
                    except Exception as e:
                        logger.error(f"Error in on_wake_word callback: {e}")

    def listen(self):
        """Start listening for wake words (blocking)."""
        logger.info(f"Starting audio stream on device {self.device_id}")
        fs = 16000
        
        self.running = True
        try:
            with sd.InputStream(samplerate=fs, 
                               blocksize=self.chunk_size, 
                               device=self.device_id, 
                               channels=1, 
                               dtype='int16', 
                               callback=self._audio_callback):
                logger.info("Wake word listener is active (Press Ctrl+C to exit)")
                while self.running:
                    sd.sleep(100)
        except Exception as e:
            logger.error(f"Error in audio stream: {e}")
        finally:
            self.running = False


if __name__ == "__main__":
    # Configure logging for standalone run
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(description="Wake Word Listener")
    parser.add_argument("--model", type=str, default="alexa", help="Wake word model name")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Get microphone
    device_id = get_microphone()
    if device_id is None:
        print("Using default microphone.")
    
    # Callback
    def on_wake(model, score):
        print(f"\n>>> WAKE WORD DETECTED: {model} (Score: {score:.3f}) <<<\n")
        
        # Write timestamp to file
        try:
            dist_dir = os.getenv('DIST_FOLDER', 'dist')
            os.makedirs(dist_dir, exist_ok=True)
            file_path = os.path.join(dist_dir, "wakeword_last_detection.txt")
            
            with open(file_path, "w") as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(timestamp)
                print(f"Timestamp detected at: {file_path}")
        except Exception as e:
            print(f"Error writing to file: {e}")

    # Initialize
    listener = WakeWordListener(
        model_path=args.model,
        device_id=device_id,
        on_wake_word=on_wake,
        debug=args.debug
    )

    # Run blocking
    try:
        listener.listen()
    except KeyboardInterrupt:
        print("\nStopping...")
