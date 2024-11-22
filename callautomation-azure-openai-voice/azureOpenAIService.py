import asyncio
import base64
import os
import sys
import numpy as np
import soundfile as sf
import json
from pydantic_core import Url
from  rtclient import (
    RTLowLevelClient, 
    SessionUpdateMessage, 
    RTClient, 
    ServerVAD, 
    SessionUpdateParams, 
    InputAudioBufferAppendMessage, 
    InputAudioTranscription
    )
from azure.core.credentials import AzureKeyCredential
from models import AudioData, OutStreamingData
from scipy.signal import resample

answer_prompt_system_template = """
You're an AI assistant for an elevator company called Contoso Elevators. Customers will contact you as the first point of contact when having issues with their elevators. 
Your priority is to ensure the person contacting you or anyone else in or around the elevator is safe, if not then they should contact their local authorities.
If everyone is safe then ask the user for information about the elevators location, such as city, building and elevator number.
Also get the users name and number so that a technician who goes onsite can contact this person. Confirm with the user all the information 
they've shared that it's all correct and then let them know that you've created a ticket and that a technician should be onsite within the next 24 to 48 hours.
"""
AZURE_OPENAI_SERVICE_ENDPOINT = "<AZURE_OPENAI_SERVICE_ENDPOINT>"
AZURE_OPENAI_SERVICE_KEY = "<AZURE_OPENAI_SERVICE_KEY>"
AZURE_OPENAI_DEPLOYMENT_MODEL_NAME = "<AZURE_OPENAI_DEPLOYMENT_MODEL_NAME>"

# Global variable to store the WebSocket connection
ws = None

async def send_audio_to_external_ai(data: str):
    async with RTLowLevelClient(
        AZURE_OPENAI_SERVICE_ENDPOINT, key_credential=AzureKeyCredential(AZURE_OPENAI_SERVICE_KEY), azure_deployment=AZURE_OPENAI_DEPLOYMENT_MODEL_NAME
    ) as client:
        await client.send(
            SessionUpdateMessage(
                session=SessionUpdateParams(
                    turn_detection=ServerVAD(type="server_vad"),
                    input_audio_transcription=InputAudioTranscription(model="whisper-1"),
                )
            )
        )

        await asyncio.gather(send_audio(client, data), receive_messages(client))

async def send_audio(client: RTLowLevelClient, audio_file_path: str):
    sample_rate = 24000
    duration_ms = 100
    samples_per_chunk = sample_rate * (duration_ms / 1000)
    bytes_per_sample = 2
    bytes_per_chunk = int(samples_per_chunk * bytes_per_sample)

    extra_params = (
        {
            "samplerate": sample_rate,
            "channels": 1,
            "subtype": "PCM_16",
        }
        if audio_file_path.endswith(".raw")
        else {}
    )

    audio_data, original_sample_rate = sf.read(audio_file_path, dtype="int16", **extra_params)

    if original_sample_rate != sample_rate:
        audio_data = resample_audio(audio_data, original_sample_rate, sample_rate)

    audio_bytes = audio_data.tobytes()

    for i in range(0, len(audio_bytes), bytes_per_chunk):
        chunk = audio_bytes[i : i + bytes_per_chunk]
        base64_audio = base64.b64encode(chunk).decode("utf-8")
        await client.send(InputAudioBufferAppendMessage(audio=base64_audio))

def resample_audio(audio_data, original_sample_rate, target_sample_rate):
    number_of_samples = round(len(audio_data) * float(target_sample_rate) / original_sample_rate)
    resampled_audio = resample(audio_data, number_of_samples)
    return resampled_audio.astype(np.int16)

async def receive_messages(client: RTLowLevelClient):
    while not client.closed:
        message = await client.recv()
        if message is None:
            continue
        match message.type:
            case "session.created":
                print("Session Created Message")
                print(f"  Model: {message.session.model}")
                print(f"  Session Id: {message.session.id}")
                pass
            case "error":
                print("Error Message")
                print(f"  Error: {message.error}")
                pass
            case "input_audio_buffer.committed":
                print("Input Audio Buffer Committed Message")
                print(f"  Item Id: {message.item_id}")
                pass
            case "input_audio_buffer.cleared":
                print("Input Audio Buffer Cleared Message")
                pass
            case "input_audio_buffer.speech_started":
                print("Input Audio Buffer Speech Started Message")
                print(f"  Item Id: {message.item_id}")
                print(f"  Audio Start [ms]: {message.audio_start_ms}")
                pass
            case "input_audio_buffer.speech_stopped":
                print("Input Audio Buffer Speech Stopped Message")
                print(f"  Item Id: {message.item_id}")
                print(f"  Audio End [ms]: {message.audio_end_ms}")
                pass
            case "conversation.item.created":
                print("Conversation Item Created Message")
                print(f"  Id: {message.item.id}")
                print(f"  Previous Id: {message.previous_item_id}")
                if message.item.type == "message":
                    print(f"  Role: {message.item.role}")
                    for index, content in enumerate(message.item.content):
                        print(f"  [{index}]:")
                        print(f"    Content Type: {content.type}")
                        if content.type == "input_text" or content.type == "text":
                            print(f"  Text: {content.text}")
                        elif content.type == "input_audio" or content.type == "audio":
                            print(f"  Audio Transcript: {content.transcript}")
                pass
            case "conversation.item.truncated":
                print("Conversation Item Truncated Message")
                print(f"  Id: {message.item_id}")
                print(f" Content Index: {message.content_index}")
                print(f"  Audio End [ms]: {message.audio_end_ms}")
            case "conversation.item.deleted":
                print("Conversation Item Deleted Message")
                print(f"  Id: {message.item_id}")
            case "conversation.item.input_audio_transcription.completed":
                print("Input Audio Transcription Completed Message")
                print(f"  Id: {message.item_id}")
                print(f"  Content Index: {message.content_index}")
                print(f"  Transcript: {message.transcript}")
            case "conversation.item.input_audio_transcription.failed":
                print("Input Audio Transcription Failed Message")
                print(f"  Id: {message.item_id}")
                print(f"  Error: {message.error}")
            case "response.created":
                print("Response Created Message")
                print(f"  Response Id: {message.response.id}")
                print("  Output Items:")
                for index, item in enumerate(message.response.output):
                    print(f"  [{index}]:")
                    print(f"    Item Id: {item.id}")
                    print(f"    Type: {item.type}")
                    if item.type == "message":
                        print(f"    Role: {item.role}")
                        match item.role:
                            case "system":
                                for content_index, content in enumerate(item.content):
                                    print(f"    [{content_index}]:")
                                    print(f"      Content Type: {content.type}")
                                    print(f"      Text: {content.text}")
                            case "user":
                                for content_index, content in enumerate(item.content):
                                    print(f"    [{content_index}]:")
                                    print(f"      Content Type: {content.type}")
                                    if content.type == "input_text":
                                        print(f"      Text: {content.text}")
                                    elif content.type == "input_audio":
                                        print(f"      Audio Data Length: {len(content.audio)}")
                            case "assistant":
                                for content_index, content in enumerate(item.content):
                                    print(f"    [{content_index}]:")
                                    print(f"      Content Type: {content.type}")
                                    print(f"      Text: {content.text}")
                    elif item.type == "function_call":
                        print(f"    Call Id: {item.call_id}")
                        print(f"    Function Name: {item.name}")
                        print(f"    Parameters: {item.arguments}")
                    elif item.type == "function_call_output":
                        print(f"    Call Id: {item.call_id}")
                        print(f"    Output: {item.output}")
            case "response.done":
                print("Response Done Message")
                print(f"  Response Id: {message.response.id}")
                if message.response.status_details:
                    print(f"  Status Details: {message.response.status_details.model_dump_json()}")
                break
            case "response.output_item.added":
                print("Response Output Item Added Message")
                print(f"  Response Id: {message.response_id}")
                print(f"  Item Id: {message.item.id}")
            case "response.output_item.done":
                print("Response Output Item Done Message")
                print(f"  Response Id: {message.response_id}")
                print(f"  Item Id: {message.item.id}")

            case "response.content_part.added":
                print("Response Content Part Added Message")
                print(f"  Response Id: {message.response_id}")
                print(f"  Item Id: {message.item_id}")
            case "response.content_part.done":
                print("Response Content Part Done Message")
                print(f"  Response Id: {message.response_id}")
                print(f"  ItemPart Id: {message.item_id}")
            case "response.text.delta":
                print("Response Text Delta Message")
                print(f"  Response Id: {message.response_id}")
                print(f"  Text: {message.delta}")
            case "response.text.done":
                print("Response Text Done Message")
                print(f"  Response Id: {message.response_id}")
                print(f"  Text: {message.text}")
            case "response.audio_transcript.delta":
                print("Response Audio Transcript Delta Message")
                print(f"  Response Id: {message.response_id}")
                print(f"  Item Id: {message.item_id}")
                print(f"  Transcript: {message.delta}")
            case "response.audio_transcript.done":
                print("Response Audio Transcript Done Message")
                print(f"  Response Id: {message.response_id}")
                print(f"  Item Id: {message.item_id}")
                print(f"  Transcript: {message.transcript}")
            case "response.audio.delta":
                print("Response Audio Delta Message")
                print(f"  Response Id: {message.response_id}")
                print(f"  Item Id: {message.item_id}")
                print(f"  Audio Data Length: {len(message.delta)}")
            case "response.audio.done":
                print("Response Audio Done Message")
                print(f"  Response Id: {message.response_id}")
                print(f"  Item Id: {message.item_id}")
            case "response.function_call_arguments.delta":
                print("Response Function Call Arguments Delta Message")
                print(f"  Response Id: {message.response_id}")
                print(f"  Arguments: {message.delta}")
            case "response.function_call_arguments.done":
                print("Response Function Call Arguments Done Message")
                print(f"  Response Id: {message.response_id}")
                print(f"  Arguments: {message.arguments}")
            case "rate_limits.updated":
                print("Rate Limits Updated Message")
                print(f"  Rate Limits: {message.rate_limits}")
            case _:
                print("Unknown Message")

# async def start_conversation():
#     openai_service_endpoint = AZURE_OPENAI_SERVICE_ENDPOINT
#     openai_key = AZURE_OPENAI_SERVICE_KEY
#     openai_deployment_model = AZURE_OPENAI_DEPLOYMENT_MODEL_NAME

#     await start_realtime(openai_service_endpoint, openai_key, openai_deployment_model)
    
# async def start_realtime(endpoint: str, api_key: str, deployment_or_model: str):
#     try:
#         # asyncio.run(with_openai(file_path, out_dir))
#         realtime_streaming = RTClient(url=endpoint, key_credential=AzureKeyCredential(api_key), model= deployment_or_model)
#         print("sending session config")
#         realtime_streaming.session = create_config_message()
#         print("sent")
#         await handle_realtime_messages()
#     except Exception as error:
#         print(f"Error during startRealtime: {error}")

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

async def init_websocket(socket):
    global ws
    ws = socket

async def receive_audio_for_outbound(data):
    try:
        audio_data = AudioData
        audio_data.data=data
        audio_data.is_silent=False
        audio_data.participant =None

        out_streaming_data = OutStreamingData 
        out_streaming_data.kind="AudioData"
        out_streaming_data.audio_data=audio_data
        out_streaming_data.stop_audio=None

        json_data = json.dumps(out_streaming_data)

        if ws and ws.open:
            await ws.send(json_data)
        else:
            print("Socket connection is not open.")
    except Exception as e:
        print(e)

async def handle_realtime_messages():
    async for message in realtime_streaming.messages():
        console_log = str(message["type"])

        if message["type"] == "session.created":
            print(f"session started with id:-->{message['session']['id']}")
        elif message["type"] == "response.audio_transcript.delta":
            pass
        elif message["type"] == "response.audio.delta":
            await receive_audio_for_outbound(message.delta)
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