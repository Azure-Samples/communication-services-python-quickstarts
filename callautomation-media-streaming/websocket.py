import asyncio
import json
import websockets
from azure.communication.callautomation._shared.models import identifier_from_raw_id

async def send_data(websocket, buffer):

    print (f"Data buffer---> {type(buffer)}")
    # buffer_serialized = json.loads(buffer)
    if websocket.open:
        data = {
            "Kind": "AudioData",
            "ServerAudioData": {
                    "Data": str(buffer)
            },
            "Mark":None,
            "StopAudio": None

        }

        print (f"Data ---> {data}")

        # print (f"Data str ---> {str(data)}")

        #serialized_data = json.dumps(data)
        #print (f"Server Streaming Data ---> {serialized_data}")

        #print(isinstance(buffer_array, bytes))
        
        #Send the chunk over the WebSocket
        await websocket.send(bytes(str(data), 'utf-8'))

async def handle_client(websocket, path):
    print("Client connected")
    try:
        async for message in websocket:
            json_object = json.loads(message)
            kind = json_object['kind']
            kind = json_object.get('kind')
            if kind == 'AudioData':
                byte_data = json_object['audioData']['data']
                print(f"AudioData Data: {byte_data}")
                await send_data(websocket, bytes(byte_data, 'utf-8'))
            
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
