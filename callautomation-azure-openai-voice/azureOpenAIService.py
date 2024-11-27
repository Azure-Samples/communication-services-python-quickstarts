import asyncio
import json
from dataclasses import asdict
from pydantic_core import Url
from  rtclient import (
    RTLowLevelClient,
    SessionUpdateMessage,
    ServerVAD, 
    SessionUpdateParams, 
    InputAudioBufferAppendMessage, 
    InputAudioTranscription,
    )
from azure.core.credentials import AzureKeyCredential
import websockets
from models import AudioData, OutStreamingData, StopAudio
active_websocket:websockets = None
answer_prompt_system_template = "You are an AI assistant that helps people find information."
AZURE_OPENAI_SERVICE_ENDPOINT = ""
AZURE_OPENAI_SERVICE_KEY = ""
AZURE_OPENAI_DEPLOYMENT_MODEL_NAME = ""

async def start_conversation():
    global client
    client = RTLowLevelClient(url=AZURE_OPENAI_SERVICE_ENDPOINT, key_credential=AzureKeyCredential(AZURE_OPENAI_SERVICE_KEY), azure_deployment=AZURE_OPENAI_DEPLOYMENT_MODEL_NAME)
    await client.connect()
    await client.send(
            SessionUpdateMessage(
                session=SessionUpdateParams(
                    instructions=answer_prompt_system_template,
                    turn_detection=ServerVAD(type="server_vad"),
                    voice= 'shimmer',
                    input_audio_format='pcm16',
                    output_audio_format='pcm16',
                    input_audio_transcription=InputAudioTranscription(model="whisper-1")
                )
            )
        )
    
    asyncio.create_task(receive_messages(client))
    
async def send_audio_to_external_ai(audioData: str):
    await client.send(message=InputAudioBufferAppendMessage(type="input_audio_buffer.append", audio=audioData, _is_azure=True))

async def receive_messages(client: RTLowLevelClient):
    while not client.closed:
        message = await client.recv()
        if message is None:
            continue
        match message.type:
            case "session.created":
                print("Session Created Message")
                print(f"  Session Id: {message.session.id}")
                pass
            case "error":
                print(f"  Error: {message.error}")
                pass
            case "input_audio_buffer.cleared":
                print("Input Audio Buffer Cleared Message")
                pass
            case "input_audio_buffer.speech_started":
                print(f"Voice activity detection started at {message.audio_start_ms} [ms]")
                await stop_audio()
                pass
            case "input_audio_buffer.speech_stopped":
                pass
            case "conversation.item.input_audio_transcription.completed":
                print(f" User:-- {message.transcript}")
            case "conversation.item.input_audio_transcription.failed":
                print(f"  Error: {message.error}")
            case "response.done":
                print("Response Done Message")
                print(f"  Response Id: {message.response.id}")
                if message.response.status_details:
                    print(f"  Status Details: {message.response.status_details.model_dump_json()}")
            case "response.audio_transcript.done":
                print(f" AI:-- {message.transcript}")
            case "response.audio.delta":
                await receive_audio_for_outbound(message.delta)
                pass
            case _:
                pass
                
async def init_websocket(socket):
    global active_websocket, is_connected
    active_websocket = socket
    if active_websocket.open:
        print(active_websocket.open)

async def receive_audio_for_outbound(data: str):
    try:
        audio_data = AudioData(
            data=data,
            timestamp=None,
            is_silent=False,
            participant=None
        )
        
        out_streaming_data = OutStreamingData(
            kind="AudioData",
            audio_data=audio_data,
            stop_audio=None 
        )
        json_data = json.dumps(asdict(out_streaming_data), indent=4)
        await send_message(json_data)
        
    except Exception as e:
        print(e)

async def stop_audio():
        stop_audio = StopAudio()
        
        out_streaming_data = OutStreamingData(
            kind="StopAudio",
            audio_data=None,
            stop_audio=stop_audio 
        )
        json_data = json.dumps(asdict(out_streaming_data), indent=4)
        await send_message(json_data)

async def send_message(message: str):
    global active_websocket
    if active_websocket.open:
        try:
            await active_websocket.send(message)
            # print(message)
        except Exception as e:
            print(f"Failed to send message: {e}")
    else:
        print("WebSocket is not connected.")
