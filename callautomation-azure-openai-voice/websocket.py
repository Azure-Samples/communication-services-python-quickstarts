import asyncio
import websockets
import json
from azureOpenAIService import start_conversation, send_audio_to_external_ai

async def handle_realtime_messages(websocket):
    print('Client connected')
    await start_conversation()
    try:
        async for message in websocket:
            json_object = json.loads(message)
            kind = json_object.get('kind')
            if kind == "AudioData":
                audio_data = json_object['audioData']['data']
                await send_audio_to_external_ai(audio_data)
    except websockets.exceptions.ConnectionClosed as e:
        print('Client disconnected')

async def main():
    async with websockets.serve(handle_realtime_messages, "localhost", 5001):
        print("WebSocket server running on port 5001")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
