import asyncio
import json
import websockets

async def handle_client(websocket, path):
    print("Client connected")
    try:
        async for message in websocket:
            packet_data = json.loads(message)
            print("Transcription data:-->", packet_data)
    except websockets.exceptions.ConnectionClosedOK:
        print("Client disconnected")
    except websockets.exceptions.ConnectionClosedError as e:
        print("Connection closed with error: %s", e)
    except Exception as e:
        print("Unexpected error: %s", e)

start_server = websockets.serve(handle_client, "localhost", 5001)

print('WebSocket server running on port 5001')

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
