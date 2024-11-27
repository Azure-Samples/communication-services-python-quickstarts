import asyncio
import json
import websockets
from azure.communication.callautomation._shared.models import identifier_from_raw_id

async def send_data(websocket, buffer):
    if websocket.open:
        data = {
            "Kind": "AudioData",
            "AudioData": {
                    "Data":  buffer
            },
            "StopAudio": None

        }

        # Serialize the server streaming data
        serialized_data = json.dumps(data)
        print (f"Out Streaming Data ---> {serialized_data}")        
        #Send the chunk over the WebSocket
        await websocket.send(serialized_data)

async def stop_audio(websocket):
    if websocket.open:
        data = {
            "Kind": "StopAudio",
            "AudioData": None,
            "StopAudio": {
            }
        }

        # Serialize the server streaming data
        serialized_data = json.dumps(data)
        print (f"Out Streaming Data ---> {serialized_data}")        
        #Send the chunk over the WebSocket
        await websocket.send(serialized_data)

async def handle_client(websocket):
    print("Client connected")
    try:
        async for message in websocket:
            json_object = json.loads(message)
            kind = json_object['kind']
            if kind == 'AudioData':
                audio_data = json_object['audioData']['data']
                print(f"AudioData Data: {audio_data}")
                await send_data(websocket, audio_data)
            
    except websockets.exceptions.ConnectionClosedOK:
        print(f"Client disconnected")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Connection closed with error: %s", e)
    except Exception as e:
        print(f"Unexpected error: %s", e)

start_server = websockets.serve(handle_client, "localhost", 5001)

print('WebSocket server running on port 5001')

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()