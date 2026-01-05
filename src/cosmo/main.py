import asyncio
from aioesphomeapi import APIClient, ReconnectLogic

ESP_IP = "192.168.178.82"  # Deine ESP32 IP
ESP_PORT = 6053
ESP_PASSWORD = ""

async def main():
    cli = APIClient(ESP_IP, ESP_PORT, ESP_PASSWORD)
    
    async def on_connect():
        print("✅ Verbindung zu Cosmo steht!")
        
        # Callback wenn sich ein Sensor ändert
        def on_state_change(state):
            if hasattr(state, 'state') and state.state:
                print("🎤 Wake Word erkannt! Hier kannst du jetzt reagieren...")
        
        cli.subscribe_states(on_state_change)
        print("👂 Warte auf Wake Word 'Okay Nabu'...")
    
    async def on_disconnect(expected_disconnect):
        print("⚠️ Verbindung getrennt, versuche erneut...")
    
    async def on_connect_error(err):
        print(f"❌ Verbindungsfehler: {err}")
    
    # ReconnectLogic hält die Verbindung stabil
    reconnect = ReconnectLogic(
        client=cli,
        on_connect=on_connect,
        on_disconnect=on_disconnect,
        on_connect_error=on_connect_error,
    )
    
    await reconnect.start()
    
    # Verbindung offen halten
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
