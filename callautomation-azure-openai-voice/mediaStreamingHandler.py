import json
import asyncio
import websockets

from azureOpenAIService import send_audio_to_external_ai

async def process_websocket_message_async(stream_data):
    try:
        data = json.loads(stream_data)
        kind = data['kind']
        if kind == "AudioData":
            audio_data = data["audioData"]["data"]
            await send_audio_to_external_ai(audio_data)
    except Exception as e:
        print(f'Error processing WebSocket message: {e}')