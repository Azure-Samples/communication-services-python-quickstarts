
import ast
from pyexpat import model
import uuid
from urllib.parse import urlencode, urljoin
from azure.eventgrid import EventGridEvent, SystemEventNames
import requests
from flask import Flask, Response, request, json
from logging import INFO
import re
from azure.communication.callautomation import (
    CallAutomationClient,
    PhoneNumberIdentifier,
    RecognizeInputType,
    TextSource,
    # TranscriptionConfiguration,
    TranscriptionTransportType,
    ServerCallLocator,
    TranscriptionOptions
    )
from azure.core.messaging import CloudEvent
import time
# import openai

# from openai.api_resources import (
#     ChatCompletion
# )

# Your ACS resource connection string
ACS_CONNECTION_STRING = "<ACS_CONNECTION_STRING>"

# Cognitive service endpoint
COGNITIVE_SERVICE_ENDPOINT="<COGNITIVE_SERVICE_ENDPOINT>"

# Transport url
TRANSPORT_URL = "<TRANSPORT_URL>"

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
is_transcription_active=False
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

app = Flask(__name__)

def handle_recognize(text_to_play,caller_id,call_connection_id,context=""):
    play_source = TextSource(text=text_to_play, voice_name="en-US-NancyNeural")    
    recognize_result=call_automation_client.get_call_connection(call_connection_id).start_recognizing_media(
        dtmf_max_tones_to_collect= 8,
        input_type=RecognizeInputType.DTMF,
        target_participant=PhoneNumberIdentifier(caller_id), 
        end_silence_timeout=15, 
        dtmf_inter_tone_timeout=5,
        play_prompt=play_source,
        operation_context=context)
    app.logger.info("handle_recognize : data=%s",recognize_result) 

def handle_play(call_connection_id, text_to_play, context):     
    play_source = TextSource(text=text_to_play, voice_name= "en-US-NancyNeural") 
    call_automation_client.get_call_connection(call_connection_id).play_media_to_all(play_source,
                                                                                     operation_context=context)    
def handle_hangup(call_connection_id):     
    call_automation_client.get_call_connection(call_connection_id).hang_up(is_for_everyone=True)

@app.route("/api/incomingCall",  methods=['POST'])
def incoming_call_handler():
    app.logger.info("incoming event data")
    for event_dict in request.json:
        event = EventGridEvent.from_dict(event_dict)
        app.logger.info("incoming event data --> %s", event.data)
        if event.event_type == SystemEventNames.EventGridSubscriptionValidationEventName:
            app.logger.info("Validating subscription")
            validation_code = event.data['validationCode']
            validation_response = {'validationResponse': validation_code}
            return Response(response=json.dumps(validation_response), status=200)
        elif event.event_type =="Microsoft.Communication.IncomingCall":
            app.logger.info("Incoming call received: data=%s", 
                            event.data)  
            if event.data['from']['kind'] =="phoneNumber":
                caller_id =  event.data['from']["phoneNumber"]["value"]
            else :
                caller_id =  event.data['from']['rawId'] 
            app.logger.info("incoming call handler caller id: %s",
                            caller_id)
            incoming_call_context=event.data['incomingCallContext']
            guid =uuid.uuid4()
            query_parameters = urlencode({"callerId": caller_id})
            callback_uri = f"{CALLBACK_EVENTS_URI}/{guid}?{query_parameters}"

            app.logger.info("callback url: %s",  callback_uri)

            transcription_configuration=TranscriptionOptions(
                        transport_url=TRANSPORT_URL,
                        transport_type=TranscriptionTransportType.WEBSOCKET,
                        locale=LOCALE,
                        start_transcription=False
                        )
            answer_call_result = call_automation_client.answer_call(incoming_call_context=incoming_call_context,
                                                                    transcription=transcription_configuration,
                                                                    cognitive_services_endpoint=COGNITIVE_SERVICE_ENDPOINT,
                                                                    callback_url=callback_uri)
            app.logger.info("Answered call for connection id: %s",
                            answer_call_result.call_connection_id)
            return Response(status=200)
            
@app.route("/api/callbacks/<contextId>", methods=["POST"])
def handle_callback(contextId):    
    try:        
        global caller_id , call_connection_id
        app.logger.info("Request Json: %s", request.json)
        for event_dict in request.json:       
            event = CloudEvent.from_dict(event_dict)
            call_connection_id = event.data['callConnectionId']

            app.logger.info("%s event received for call connection id: %s, correlation id: %s", 
                            event.type, call_connection_id, event.data["correlationId"])
            caller_id = request.args.get("callerId").strip()
            if "+" not in caller_id:
                caller_id="+".strip()+caller_id.strip()

            app.logger.info("call connected : data=%s", event.data)
            if event.type == "Microsoft.Communication.CallConnected":
                # Start the recording 
                recording_result = call_automation_client.start_recording(
                    call_locator=ServerCallLocator(event.data["serverCallId"]))
                global recording_id
                recording_id=recording_result.recording_id

                global call_properties
                call_properties = call_automation_client.get_call_connection(call_connection_id).get_call_properties()
                app.logger.info("Transcription subscription--->=%s", call_properties.transcription_subscription)

                # Start the transcription 
                initiate_transcription(call_connection_id)
                time.sleep(3)
                pause_or_stop_transcription_and_recording(call_connection_id=call_connection_id, stop_recording=False, recording_id=recording_id)
                time.sleep(3)
                handle_recognize(HELP_IVR_PROMPT,
                                  caller_id,call_connection_id,
                                  context="hellocontext") 
            elif event.type == "Microsoft.Communication.PlayCompleted":
                context=event.data['operationContext']    
                app.logger.info("Play completed: context=%s", event.data['operationContext'])
                if context == ADD_AGENT_CONTEXT:
                    #Add agent
                    target = PhoneNumberIdentifier(AGENT_PHONE_NUMBER)
                    source_caller_id_number = PhoneNumberIdentifier(ACS_PHONE_NUMBER)
                    call_connection = call_automation_client.get_call_connection(call_connection_id)
                    add_participant_result=call_connection.add_participant(target_participant=target, 
                                                                           source_caller_id_number=source_caller_id_number, 
                                                                           operation_context=None,
                                                                           invitation_timeout=15)
                    app.logger.info("Add agent to the call: %s", add_participant_result.invitation_id)
                elif context == GOODBYE_CONTEXT or context == ADD_PARTICIPANT_FAILURE_CONTEXT:
                    pause_or_stop_transcription_and_recording(call_connection_id, stop_recording=True,recording_id=recording_id)
                    handle_hangup(call_connection_id=call_connection_id)
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
                        resume_transcription_and_recording(call_connection_id, recording_id)
                        handle_play(call_connection_id, ADD_AGENT_PROMPT, ADD_AGENT_CONTEXT)
                    else:
                        handle_recognize(INCORRECT_DOB_PROMPT, caller_id, call_connection_id, INCORRECT_DOB_CONTEXT)
            elif event.type == "Microsoft.Communication.RecognizeFailed":
                resultInformation = event.data['resultInformation']
                app.logger.info("Recognize failed event received: message=%s, subcode=%s", resultInformation['message'],resultInformation['subCode'])
                reasonCode = resultInformation['subCode']
                context=event.data['operationContext']
                global max_retry
                if reasonCode == 8510 and 0 < max_retry:
                    handle_recognize(TIMEOUT_SILENCE_PROMPT,caller_id,call_connection_id, context="retryContext") 
                    max_retry -= 1
                else:
                    handle_play(call_connection_id=call_connection_id,text_to_play=GOODBYE_PROMPT, context=GOODBYE_CONTEXT) 
            elif event.type == "Microsoft.Communication.AddParticipantFailed":
                resultInformation = event.data['resultInformation']
                app.logger.info("Received Add Participants Failed message=%s, subcode=%s",resultInformation['message'],resultInformation['subCode'])
                handle_play(call_connection_id=call_connection_id,text_to_play=ADD_PARTICIPANT_FAILURE_PROMPT, context=ADD_PARTICIPANT_FAILURE_CONTEXT)
                
            elif event.type == "Microsoft.Communication.TranscriptionStarted":
                app.logger.info("Received TranscriptionStarted event.")
                transcriptionUpdate = event.data['transcriptionUpdate']
                app.logger.info(event.data['operationContext'])
                app.logger.info(transcriptionUpdate["transcriptionStatus"])
                app.logger.info(transcriptionUpdate["transcriptionStatusDetails"])
            elif event.type == "Microsoft.Communication.TranscriptionStopped":
                app.logger.info("Received TranscriptionStopped event.")
                transcriptionUpdate = event.data['transcriptionUpdate']
                app.logger.info(transcriptionUpdate["transcriptionStatus"])
                app.logger.info(transcriptionUpdate["transcriptionStatusDetails"])
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
def recording_file_status():
    try:
        for event_dict in request.json:
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

@app.route('/api/download')
def download_recording():
        try:
            app.logger.info("Content location : %s", content_location)
            recording_data = call_automation_client.download_recording(content_location)
            with open("Recording_File.wav", "wb") as binary_file:
                binary_file.write(recording_data.read())
            return Response(response="Ok")
        except Exception as ex:
            app.logger.info("Failed to download recording --> " + str(ex))
            return Response(text=str(ex), status=500)
        
def initiate_transcription(call_connection_id):
    app.logger.info("initiate_transcription is called %s", call_connection_id)
    callconnection = call_automation_client.get_call_connection(call_connection_id)
    callconnection.start_transcription(locale=LOCALE, operation_context="StartTranscript")
    app.logger.info("Starting the transcription")
    global is_transcription_active
    is_transcription_active=True

def pause_or_stop_transcription_and_recording(call_connection_id, stop_recording, recording_id):
    app.logger.info("pause_or_stop_transcription_and_recording method triggerd.")
    global is_transcription_active
    app.logger.info("is_transcription_active: %s", is_transcription_active)
    app.logger.info("stop_recording: %s", stop_recording)
    if is_transcription_active:
        app.logger.info("Transcription is active and attempted to stop the transcription for the call id %s", call_connection_id)           
        call_automation_client.get_call_connection(call_connection_id).stop_transcription()
        is_transcription_active=False
        app.logger.info("Transcription stopped.")

    if stop_recording:
        call_automation_client.stop_recording(recording_id=recording_id)
        app.logger.info(f"Recording stopped. RecordingId: {recording_id}")
    else:
        call_automation_client.pause_recording(recording_id=recording_id)  
        app.logger.info(f"Recording paused. RecordingId: {recording_id}")

def resume_transcription_and_recording(call_connection_id, recording_id):
    initiate_transcription(call_connection_id)    
    app.logger.info("Transcription reinitiated.")

    call_automation_client.resume_recording(recording_id)
    app.logger.info(f"Recording resumed. RecordingId: {recording_id}")

@app.route("/")
def hello():
    return "Hello ACS CallAutomation!..test"

if __name__ == '__main__':
    app.logger.setLevel(INFO)
    app.run(port=8080)
