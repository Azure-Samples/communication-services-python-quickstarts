import json
import os
import asyncio
from  rtclient import RTLowLevelClient, SessionUpdateMessage

answer_prompt_system_template = """
You're an AI assistant for an elevator company called Contoso Elevators. Customers will contact you as the first point of contact when having issues with their elevators. 
Your priority is to ensure the person contacting you or anyone else in or around the elevator is safe, if not then they should contact their local authorities.
If everyone is safe then ask the user for information about the elevators location, such as city, building and elevator number.
Also get the users name and number so that a technician who goes onsite can contact this person. Confirm with the user all the information 
they've shared that it's all correct and then let them know that you've created a ticket and that a technician should be onsite within the next 24 to 48 hours.
"""

realtime_streaming = None

async def send_audio_to_external_ai(data: str):
    try:
        audio = data
        await realtime_streaming.send({
            "type": "input_audio_buffer.append",
            "audio": audio,
        })
    except Exception as e:
        print(e)

async def start_conversation():
    openai_service_endpoint = os.getenv("AZURE_OPENAI_SERVICE_ENDPOINT")
    openai_key = os.getenv("AZURE_OPENAI_SERVICE_KEY")
    openai_deployment_model = os.getenv("AZURE_OPENAI_DEPLOYMENT_MODEL_NAME")

    await start_realtime(openai_service_endpoint, openai_key, openai_deployment_model)

async def start_realtime(endpoint: str, api_key: str, deployment_or_model: str):
    global realtime_streaming
    try:
        realtime_streaming = RTLowLevelClient(endpoint, {"key": api_key}, {"deployment": deployment_or_model})
        print("sending session config")
        await realtime_streaming.send(create_config_message())
        print("sent")
        await handle_realtime_messages()
    except Exception as error:
        print(f"Error during startRealtime: {error}")

def create_config_message() -> SessionUpdateMessage:
    config_message = {
        "type": "session.update",
        "session": {
            "instructions": answer_prompt_system_template,
            "voice": "alloy",
            "input_audio_format": "pcm16",
            "output_audio_format": "pcm16",
            "turn_detection": {
                "type": "server_vad",
            },
            "input_audio_transcription": {
                "model": "whisper-1"
            }
        }
    }
    return config_message

async def handle_realtime_messages():
    async for message in realtime_streaming.messages():
        console_log = str(message["type"])

        if message["type"] == "session.created":
            print(f"session started with id:-->{message['session']['id']}")
        elif message["type"] == "response.audio_transcript.delta":
            pass
        elif message["type"] == "response.audio.delta":
            pass
        elif message["type"] == "input_audio_buffer.speech_started":
            pass
        elif message["type"] == "conversation.item.input_audio_transcription.completed":
            pass
        elif message["type"] == "response.done":
            pass
        else:
            console_log = json.dumps(message, indent=2)

        if console_log:
            print(console_log)
