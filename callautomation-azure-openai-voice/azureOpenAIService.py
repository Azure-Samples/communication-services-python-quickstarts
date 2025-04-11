import json

import openai
from openai import AsyncAzureOpenAI
from openai.types.beta.realtime.session import Session
from openai.resources.beta.realtime.realtime import AsyncRealtimeConnection, AsyncRealtimeConnectionManager

import asyncio
import json
import random

from azure.core.credentials import AzureKeyCredential

AZURE_OPENAI_API_ENDPOINT = '<AZURE_OPENAI_SERVICE_ENDPOINT>'
AZURE_OPENAI_API_VERSION = "2024-10-01-preview"
AZURE_OPENAI_API_KEY = '<AZURE_OPENAI_SERVICE_KEY>'
AZURE_OPENAI_DEPLOYMENT_NAME = '<AZURE_OPENAI_DEPLOYMENT_MODEL_NAME>'
SAMPLE_RATE = 24000

def session_config():
    """Returns a random value from the predefined list."""
    values = ['alloy', 'ash', 'ballad', 'coral', 'echo', 'sage', 'shimmer', 'verse']
    ### for details on available param: https://platform.openai.com/docs/api-reference/realtime-sessions/create
    SESSION_CONFIG={
        "input_audio_transcription": {
            "model": "whisper-1",
        },
        "turn_detection": {
            "threshold": 0.4,
            "silence_duration_ms": 600,
            "type": "server_vad"
        },
        "instructions": "Your name is Sam, you work for Contoso Services. You're a helpful, calm and cheerful agent who responds with a clam British accent, but also can speak in any language or accent. Always start the conversation with a cheery hello, stating your name and who do you work for!",
        "voice": random.choice(values),
        "modalities": ["text", "audio"] ## required to solicit the initial welcome message
    }
    return SESSION_CONFIG

class OpenAIRTHandler():
    incoming_websocket = None
    client = None
    connection = None
    connection_manager = None
    welcomed = False

    def __init__(self) -> None:
        print("Hello World")
        self.client = AsyncAzureOpenAI(
                azure_endpoint=AZURE_OPENAI_API_ENDPOINT,
                azure_deployment=AZURE_OPENAI_DEPLOYMENT_NAME,
                api_key=AZURE_OPENAI_API_KEY,
                api_version=AZURE_OPENAI_API_VERSION,
            )
        self.connection_manager = self.client.beta.realtime.connect(
                    model="gpt-4o-realtime-preview"  # Replace with your deployed realtime model id on Azure OpenAI.
            )

    def __exit__(self, exc_type, exc_value, traceback):
        self.connection.close()
        self.incoming_websocket.close()

#start_conversation > start_client
    async def start_client(self):
            self.connection = await self.connection_manager.enter()
            await self.connection.session.update(session=session_config())
            await self.connection.response.create()
            ### running an async task to listen and recieve oai messages
            asyncio.create_task(self.receive_oai_messages())

#send_audio_to_external_ai > audio_to_oai        
    async def audio_to_oai(self, audioData: str):
        await self.connection.input_audio_buffer.append(audio=audioData)

#receive_messages > receive_oai_messages
    async def receive_oai_messages(self):
            #while not self.connection._connection.close_code:
                async for event in self.connection:
                    #print(event)
                    if event is None:
                        continue
                    match event.type:
                        case "session.created":
                            print("Session Created Message")
                            print(f"  Session Id: {event.session.id}")
                            pass
                        case "error":
                            print(f"  Error: {event.error}")
                            pass
                        case "input_audio_buffer.cleared":
                            print("Input Audio Buffer Cleared Message")
                            pass
                        case "input_audio_buffer.speech_started":
                            print(f"Voice activity detection started at {event.audio_start_ms} [ms]")
                            await self.stop_audio()
                            pass
                        case "input_audio_buffer.speech_stopped":
                            pass
                        case "conversation.item.input_audio_transcription.completed":
                            print(f" User:-- {event.transcript}")
                        case "conversation.item.input_audio_transcription.failed":
                            print(f"  Error: {event.error}")
                        case "response.done":
                            print("Response Done Message")
                            print(f"  Response Id: {event.response.id}")
                            if event.response.status_details:
                                print(f"  Status Details: {event.response.status_details.model_dump_json()}")
                        case "response.audio_transcript.done":
                            print(f" AI:-- {event.transcript}")
                        case "response.audio.delta":
                            await self.oai_to_acs(event.delta)
                            pass
                        case _:
                            pass
                    
#init_websocket -> init_incoming_websocket (incoming)
    async def init_incoming_websocket(self, socket):
        # print("--inbound socket set")
        self.incoming_websocket = socket

#receive_audio_for_outbound > oai_to_acs
    async def oai_to_acs(self, data):
        try:
            data = {
                "Kind": "AudioData",
                "AudioData": {
                        "Data":  data
                },
                "StopAudio": None
            }

            # Serialize the server streaming data
            serialized_data = json.dumps(data)
            await self.send_message(serialized_data)
            
        except Exception as e:
            print(e)

# stop oai talking when detecting the user talking
    async def stop_audio(self):
            stop_audio_data = {
                "Kind": "StopAudio",
                "AudioData": None,
                "StopAudio": {}
            }

            json_data = json.dumps(stop_audio_data)
            await self.send_message(json_data)

# send_message > send_message
    async def send_message(self, message: str):
        try:
            await self.incoming_websocket.send(message)
        except Exception as e:
            print(f"Failed to send message: {e}")

    async def send_welcome(self):
        if not self.welcomed:
            await self.connection.conversation.item.create(
            item={
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "Hi! What's your name and who do you work for?"}],
                }
            )
            await self.connection.response.create()
            self.welcomed = True

#mediaStreamingHandler.process_websocket_message_async -> acs_to_oai
    async def acs_to_oai(self, stream_data):
        try:
            data = json.loads(stream_data)
            kind = data['kind']
            if kind == "AudioData":
                audio_data = data["audioData"]["data"]
                await self.audio_to_oai(audio_data)
        except Exception as e:
            print(f'Error processing WebSocket message: {e}')