
import ast
import uuid
import os
from pathlib import Path
from urllib.parse import urlencode, urljoin, urlparse, urlunparse
from azure.eventgrid import EventGridEvent, SystemEventNames
import requests
from quart import Quart, Response, request, json, redirect, websocket, render_template
import json
from logging import INFO
import re
from azure.communication.callautomation import (
    PhoneNumberIdentifier,
    RecognizeInputType,
    TextSource,
    # TranscriptionConfiguration,
    TranscriptionTransportType,
    ServerCallLocator,
    TranscriptionOptions,
    RecordingContent,
    RecordingChannel,
    RecordingFormat
    )
from azure.communication.callautomation.aio import (
    CallAutomationClient
    )
from azure.core.messaging import CloudEvent
import time
import asyncio
import json
from azure.communication.callautomation._shared.models import identifier_from_raw_id
from transcriptionDataHandler import process_websocket_message_async
# import openai

# from openai.api_resources import (
#     ChatCompletion
# )

# Your ACS resource connection string
ACS_CONNECTION_STRING = "<ACS_CONNECTION_STRING>"

# Cognitive service endpoint
COGNITIVE_SERVICE_ENDPOINT="<COGNITIVE_SERVICE_ENDPOINT>"

# Acs Phone Number
ACS_PHONE_NUMBER="<ACS_PHONE_NUMBER>"

# Transcription Locale
LOCALE="<LOCALE>"

# Agent Phone Number
AGENT_PHONE_NUMBER="<AGENT_PHONE_NUMBER>"

# Callback events URI to handle callback events.
CALLBACK_URI_HOST = "<CALLBACK_URI_HOST>"
CALLBACK_EVENTS_URI = CALLBACK_URI_HOST + "/api/callbacks"

HELP_IVR_PROMPT = "Welcome to the Contoso Utilities. To access your account, we need to verify your identity. Please enter your date of birth in the format DDMMYYYY using the keypad on your phone. Once we’ve validated your identity we will connect you to the next available agent. Please note this call will be recorded!"
ADD_AGENT_PROMPT = "Thank you for verifying your identity. We are now connecting you to the next available agent. Please hold the line and we will be with you shortly. Thank you for your patience."
INCORRECT_DOB_PROMPT = "Sorry, we were unable to verify your identity based on the date of birth you entered. Please try again. Remember to enter your date of birth in the format DDMMYYYY using the keypad on your phone. Once you've entered your date of birth, press the pound key. Thank you!"
ADD_PARTICIPANT_FAILURE_PROMPT = "We're sorry, we were unable to connect you to an agent at this time, we will get the next available agent to call you back as soon as possible."
GOODBYE_PROMPT = "Thank you for calling Contoso Utilities. We hope we were able to assist you today. Goodbye"
TIMEOUT_SILENCE_PROMPT = "I’m sorry, I didn’t receive any input. Please type your date of birth in the format of DDMMYYYY."
GOODBYE_CONTEXT = "Goodbye"
ADD_AGENT_CONTEXT = "AddAgent"
INCORRECT_DOB_CONTEXT = "IncorrectDob"
ADD_PARTICIPANT_FAILURE_CONTEXT = "FailedToAddParticipant"
INCOMING_CALL_CONTEXT = "incomingCallContext"

DOB_REGEX = r"^(0[1-9]|[12][0-9]|3[01])(0[1-9]|1[012])[12][0-9]{3}$"

call_automation_client = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)

recording_id = None
recording_chunks_location = []
recording_callback_url = None
max_retry = 2
words_to_numbers = {
    'one': 1,
    'two': 2,
    'three': 3,
    'four': 4,
    'five': 5,
    'six': 6,
    'seven': 7,
    'eight': 8,
    'nine': 9,
    'zero': 0
    }

TEMPLATE_FILES_PATH = "template"
app = Quart(__name__,
            template_folder=TEMPLATE_FILES_PATH)

async def handle_recognize(text_to_play,caller_id,call_connection_id,context=""):
    play_source = TextSource(text=text_to_play, voice_name="en-US-NancyNeural")
    connection_client = call_automation_client.get_call_connection(call_connection_id)
    try:
        recognize_result = await connection_client.start_recognizing_media( 
    dtmf_max_tones_to_collect=8,
    input_type=RecognizeInputType.DTMF,
    target_participant=PhoneNumberIdentifier(caller_id),
    end_silence_timeout=15,
    dtmf_inter_tone_timeout=5,
    play_prompt=play_source,
    operation_context=context)
        app.logger.info("handle_recognize : data=%s",recognize_result)
    except Exception as ex:
        app.logger.info("Error in recognize: %s", ex)

async def handle_play(call_connection_id, text_to_play, context):     
    play_source = TextSource(text=text_to_play, voice_name= "en-US-NancyNeural") 
    await call_automation_client.get_call_connection(call_connection_id).play_media_to_all(play_source,operation_context=context)  

async def handle_hangup(call_connection_id):     
    await call_automation_client.get_call_connection(call_connection_id).hang_up(is_for_everyone=True)

@app.route("/api/incomingCall", methods=['POST'])
async def incoming_call_handler():
    app.logger.info("Received incoming call event.")
    try:
        for event_dict in await request.json:
            event = EventGridEvent.from_dict(event_dict)
            app.logger.info("incoming event data --> %s", event.data)
            if event.event_type == SystemEventNames.EventGridSubscriptionValidationEventName:
                app.logger.info("Validating subscription")
                validation_code = event.data['validationCode']
                return Response(response=json.dumps({"validationResponse": validation_code}), status=200)

            if event.event_type == "Microsoft.Communication.IncomingCall":
                app.logger.info("Incoming call received: data=%s", event.data) 
                if event.data['from']['kind'] =="phoneNumber":
                    caller_id =  event.data['from']["phoneNumber"]["value"]
                else :
                    caller_id =  event.data['from']['rawId'] 
                app.logger.info("incoming call handler caller id: %s",
                            caller_id)
                incoming_call_context = event.data['incomingCallContext']
                guid = uuid.uuid4()
                callback_uri = f"{CALLBACK_EVENTS_URI}/{guid}?callerId={caller_id}"
                websocket_url = urlunparse(("wss", urlparse(CALLBACK_URI_HOST).netloc, "/ws", "", "", ""))
                global recording_callback_url
                recording_callback_url = callback_uri
                transcription_config = TranscriptionOptions(
                    transport_url=websocket_url,
                    transport_type=TranscriptionTransportType.WEBSOCKET,
                    locale=LOCALE,
                    start_transcription=True
                )

                try:
                    answer_call_result = await call_automation_client.answer_call(
                        incoming_call_context=incoming_call_context,
                        transcription=transcription_config,
                        cognitive_services_endpoint=COGNITIVE_SERVICE_ENDPOINT,
                        callback_url=callback_uri
                    )
                    app.logger.info(f"Call answered, connection ID: {answer_call_result.call_connection_id}")
                except Exception as e:
                    app.logger.error(f"Failed to answer call: {e}")
                    return Response(status=500)
        return Response(status=200)
    except Exception as ex:
        app.logger.error(f"Error handling incoming call: {ex}")
        return Response(status=500)
            
@app.route("/api/callbacks/<contextId>", methods=["POST"])
async def handle_callback(contextId):    
    try:        
        global caller_id , call_connection_id
        # app.logger.info("Request Json: %s", request.json)
        for event_dict in await request.json:       
            event = CloudEvent.from_dict(event_dict)
            call_connection_id = event.data['callConnectionId']

            app.logger.info("%s event received for call connection id: %s, correlation id: %s", 
                            event.type, call_connection_id, event.data["correlationId"])
            caller_id = request.args.get("callerId").strip()
            if "+" not in caller_id:
                caller_id="+".strip()+caller_id.strip()

            app.logger.info("call connected : data=%s", event.data)
            if event.type == "Microsoft.Communication.CallConnected":
                recording_result = await call_automation_client.start_recording(
                    server_call_id=event.data["serverCallId"],
                    recording_content_type=RecordingContent.AUDIO_VIDEO,
                    recording_channel_type=RecordingChannel.MIXED,
                    recording_format_type=RecordingFormat.MP4,
                    recording_state_callback_url=recording_callback_url,
                    pause_on_start=True
                    )
                global recording_id
                recording_id=recording_result.recording_id
                global call_properties
                call_properties = await call_automation_client.get_call_connection(call_connection_id).get_call_properties()
                app.logger.info("Transcription subscription--->=%s", call_properties.transcription_subscription)
                
            elif event.type == "Microsoft.Communication.PlayStarted":
                app.logger.info("Received PlayStarted event.")
            elif event.type == "Microsoft.Communication.PlayCompleted":
                context=event.data['operationContext']  
                app.logger.info("Play completed: context=%s", event.data['operationContext']) 
                if context == ADD_AGENT_CONTEXT:
                    app.logger.info("Add agent to the call: %s", ADD_AGENT_CONTEXT) 
                    #Add agent
                    target = PhoneNumberIdentifier(AGENT_PHONE_NUMBER)
                    source_caller_id_number = PhoneNumberIdentifier(ACS_PHONE_NUMBER)
                    app.logger.info("source_caller_id_number: %s", source_caller_id_number) 
                    call_connection = call_automation_client.get_call_connection(call_connection_id)
                    add_participant_result= await call_connection.add_participant(target_participant=target, 
                                                                        source_caller_id_number=source_caller_id_number, 
                                                                        operation_context=None,
                                                                        invitation_timeout=15)
                    app.logger.info("Add agent to the call: %s", add_participant_result.invitation_id)
                elif context == GOODBYE_CONTEXT or context == ADD_PARTICIPANT_FAILURE_CONTEXT:
                    await stop_transcription_and_recording(call_connection_id, recording_id=recording_id)
                    await handle_hangup(call_connection_id=call_connection_id)
            elif event.type == "Microsoft.Communication.RecognizeCompleted":
                app.logger.info("Recognize completed: data=%s", event.data)
                if event.data['recognitionType'] == "dtmf": 
                    dtmf_tones = event.data['dtmfResult']['tones']; 
                    app.logger.info("Recognition completed, dtmf tones =%s", dtmf_tones)
                    global words_to_numbers 
                    numbers = "".join(str(words_to_numbers [x]) for x in dtmf_tones)
                    regex = re.compile(DOB_REGEX)
                    match = regex.search(numbers)
                    if match:
                        await resume_transcription_and_recording(call_connection_id, recording_id)
                    else:
                        await handle_recognize(INCORRECT_DOB_PROMPT, caller_id, call_connection_id, INCORRECT_DOB_CONTEXT)
            elif event.type == "Microsoft.Communication.RecognizeFailed":
                resultInformation = event.data['resultInformation']
                app.logger.info("Recognize failed event received: message=%s, sub code=%s", resultInformation['message'],resultInformation['subCode'])
                reasonCode = resultInformation['subCode']
                context=event.data['operationContext']
                global max_retry
                if reasonCode == 8510 and 0 < max_retry:
                    await handle_recognize(TIMEOUT_SILENCE_PROMPT,caller_id,call_connection_id, context="retryContext") 
                    max_retry -= 1
                else:
                    await handle_play(call_connection_id=call_connection_id,text_to_play=GOODBYE_PROMPT, context=GOODBYE_CONTEXT) 
            elif event.type == "Microsoft.Communication.AddParticipantFailed":
                resultInformation = event.data['resultInformation']
                app.logger.info("Received Add Participants Failed message=%s, sub code=%s",resultInformation['message'],resultInformation['subCode'])
                await handle_play(call_connection_id=call_connection_id,text_to_play=ADD_PARTICIPANT_FAILURE_PROMPT, context=ADD_PARTICIPANT_FAILURE_CONTEXT)
            elif event.type == "Microsoft.Communication.RecordingStateChanged":
                app.logger.info("Received RecordingStateChanged event.")
                app.logger.info(event.data['state'])
            elif event.type == "Microsoft.Communication.TranscriptionStarted":
                app.logger.info("Received TranscriptionStarted event.")
                operation_context = None
                if 'operationContext' in event.data:
                    operation_context = event.data['operationContext']
                
                if operation_context is None:
                    await call_automation_client.get_call_connection(event.data['callConnectionId']).stop_transcription(operation_context="nextRecognizeContext")
                elif operation_context is not None and operation_context == 'StartTranscriptionContext':
                    await handle_play(event.data['callConnectionId'], ADD_AGENT_PROMPT, ADD_AGENT_CONTEXT)
                
            elif event.type == "Microsoft.Communication.TranscriptionStopped":
                app.logger.info("Received TranscriptionStopped event.")
                operation_context = None
                if 'operationContext' in event.data:
                    operation_context = event.data['operationContext']

                if operation_context is not None and operation_context == 'nextRecognizeContext':
                    await handle_recognize(HELP_IVR_PROMPT,caller_id,call_connection_id,context="hellocontext")
                
            elif event.type == "Microsoft.Communication.TranscriptionUpdated":
                app.logger.info("Received TranscriptionUpdated event.")
                transcriptionUpdate = event.data['transcriptionUpdate']
                app.logger.info(transcriptionUpdate["transcriptionStatus"])
                app.logger.info(transcriptionUpdate["transcriptionStatusDetails"])
            elif event.type == "Microsoft.Communication.TranscriptionFailed":
                app.logger.info("Received TranscriptionFailed event.")
                resultInformation = event.data['resultInformation']
                app.logger.info("Encountered error during Transcription, message=%s, code=%s, subCode=%s", 
                                    resultInformation['message'], 
                                    resultInformation['code'],
                                    resultInformation['subCode'])
        return Response(status=200) 
    except Exception as ex:
        app.logger.info("error in event handling")

@app.route('/api/recordingFileStatus', methods=['POST'])
async def recording_file_status():
    try:
        for event_dict in await request.json:
            event = EventGridEvent.from_dict(event_dict)
            if event.event_type ==  SystemEventNames.EventGridSubscriptionValidationEventName:
                code = event.data['validationCode']
                if code:
                    data = {"validationResponse": code}
                    app.logger.info("Successfully Subscribed EventGrid.ValidationEvent --> " + str(data))
                    return Response(response=str(data), status=200)

            if event.event_type == SystemEventNames.AcsRecordingFileStatusUpdatedEventName:
                acs_recording_file_status_updated_event_data = event.data
                acs_recording_chunk_info_properties = acs_recording_file_status_updated_event_data['recordingStorageInfo']['recordingChunks'][0]
                app.logger.info("acsRecordingChunkInfoProperties response data --> " + str(acs_recording_chunk_info_properties))
                global content_location
                content_location = acs_recording_chunk_info_properties['contentLocation']
                return Response(response="Ok")  
                                                
    except Exception as ex:
        app.logger.error( "Failed to get recording file")
        return Response(response='Failed to get recording file', status=400)

@app.route('/download')
async def download_recording():
        try:
            app.logger.info("Content location : %s", content_location)
            downloads_folder = str(Path.home() / "Downloads")
            file_path = os.path.join(downloads_folder, "Recording_File.mp4")

            recording_data = await call_automation_client.download_recording(content_location)
            with open(file_path, "wb") as binary_file:
                binary_file.write(await recording_data.read())
            return redirect("/")
        except Exception as ex:
            app.logger.info("Failed to download recording --> " + str(ex))
            return Response(text=str(ex), status=500)
        
async def initiate_transcription(call_connection_id):
    app.logger.info("initiate_transcription is called %s", call_connection_id)
    call_connection = call_automation_client.get_call_connection(call_connection_id)
    await call_connection.start_transcription(locale=LOCALE, operation_context="StartTranscriptionContext")
    app.logger.info("Starting the transcription")
    
async def stop_transcription_and_recording(call_connection_id, recording_id):
    app.logger.info("stop_transcription_and_recording method triggered.")
    call_properties = await call_automation_client.get_call_connection(call_connection_id).get_call_properties()
    recording_properties = await call_automation_client.get_recording_properties(recording_id)
    if call_properties.transcription_subscription.state == 'active':
        await call_automation_client.get_call_connection(call_connection_id).stop_transcription()
    if recording_properties.recording_state == "active":
        await call_automation_client.stop_recording(recording_id=recording_id)

async def resume_transcription_and_recording(call_connection_id, recording_id):
    await initiate_transcription(call_connection_id)    
    app.logger.info("Transcription re initiated.")

    await call_automation_client.resume_recording(recording_id)
    app.logger.info(f"Recording resumed. RecordingId: {recording_id}")
    
    # WebSocket.
@app.websocket('/ws')
async def ws():
    print("Client connected to WebSocket")
    try:
        while True:
            try:
                # Receive data from the client
                message = await websocket.receive()
                await process_websocket_message_async(message)
            except Exception as e:
                print(f"Error while receiving message: {e}")
                break  # Close connection on error
    except Exception as e:
        print(f"WebSocket connection closed: {e}")
    finally:
        # Any cleanup or final logs can go here
        print("WebSocket connection closed")

@app.route('/')
async def index_handler():
    return await render_template("index.html")

if __name__ == '__main__':
    app.logger.setLevel(INFO)
    app.run(port=8080)