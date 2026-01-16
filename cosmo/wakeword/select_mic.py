import sounddevice as sd
import os
from dotenv import load_dotenv, set_key
from pathlib import Path

def get_microphone():
    """
    Checks for SELECTED_MIC env var. If not present or -1, prompts user to select a device.
    Updates .env file with the selection.
    Returns the device ID (int).
    """
    # Load env vars from .env file
    env_path = Path('.env')
    load_dotenv(dotenv_path=env_path)
    
    selected_mic = os.getenv('SELECTED_MIC')
    
    # Try to parse existing selection
    device_id = -1
    if selected_mic is not None:
        try:
            device_id = int(selected_mic)
        except ValueError:
            device_id = -1
            
    # Return immediately if valid selection exists
    if device_id != -1:
        return device_id
        
    # No valid selection found, prompt user
    print("\n--- Audio Input Selection ---")
    devices = sd.query_devices()
    input_devices = []
    
    print(f"{'ID':<4} {'Name':<40} {'Channels':<10}")
    print("-" * 60)
    
    seen_names = set()
    
    for i, dev in enumerate(devices):
        # Filter for input devices (max_input_channels > 0)
        if dev['max_input_channels'] > 0:
            name = dev['name']
            
            # Skip Microsoft Sound Mapper (it just points to default)
            if "Microsoft Sound Mapper" in name:
                continue
                
            # Skip duplicates (different Host APIs often show same device)
            if name in seen_names:
                continue
                
            seen_names.add(name)
            input_devices.append(i)
            print(f"{i:<4} {name:<40} {dev['max_input_channels']:<10}")
            
    if not input_devices:
        print("No input devices found!")
        return None
        
    while True:
        try:
            selection = input("Select Microphone ID: ")
            sel_id = int(selection)
            if sel_id in input_devices:
                # Save to .env
                if not env_path.exists():
                    env_path.touch()
                
                set_key(env_path, 'SELECTED_MIC', str(sel_id))
                print(f"Saved selection to .env: SELECTED_MIC={sel_id}")
                return sel_id
            else:
                print("Invalid ID, please choose from the list above.")
        except ValueError:
            print("Please enter a number.")
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
            return None

if __name__ == "__main__":
    mic = get_microphone()
    if mic is not None:
        print(f"Selected Microphone ID: {mic}")
