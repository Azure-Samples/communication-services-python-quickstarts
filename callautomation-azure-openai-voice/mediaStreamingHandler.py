import json
import asyncio
import websockets

from azureOpenAIService import send_audio_to_external_ai

async def process_websocket_message_async(stream_data):
    try:
        json_object = stream_data
        kind = json_object.get('kind')
        if kind == "AudioData":
            audio_data = json_object['audioData']['data']
            await send_audio_to_external_ai(audio_data)
    except Exception as e:
        print(f'Error processing WebSocket message: {e}')