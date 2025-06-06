import json
from azureOpenAIService import send_audio_to_external_ai

async def process_websocket_message_async(stream_data):
    try:
        data = json.loads(stream_data)
        kind = data.get('kind')
        if kind == "AudioData":
            audio_data_section = data.get("audioData", {})
            if not audio_data_section.get("silent", True):
                audio_data = audio_data_section.get("data")
                await send_audio_to_external_ai(audio_data)

    except Exception as e:
        print(f'Error processing WebSocket message: {e}')