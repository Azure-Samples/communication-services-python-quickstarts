
from pyexpat import model
import time
import uuid
from urllib.parse import urlencode, urljoin
from azure.eventgrid import EventGridEvent, SystemEventNames
import requests
from flask import Flask, Response, request, json,render_template,redirect
from logging import INFO
import re
from azure.communication.callautomation import (
    CallAutomationClient,
    PhoneNumberIdentifier,
    RecognizeInputType,
    TextSource,
    CommunicationUserIdentifier,
    ServerCallLocator,
    RecordingChannel,
    RecordingContent,
    RecordingFormat,
    AzureBlobContainerRecordingStorage,
    AzureCommunicationsRecordingStorage
    )
from azure.core.messaging import CloudEvent

COMMUNICATION_USR_ID = ""

# Your ACS resource connection string
ACS_CONNECTION_STRING = ""

# Cognitive service endpoint
COGNITIVE_SERVICE_ENDPOINT=""

# Agent Phone Number
TARGET_PHONE_NUMBER=""

ACS_PHONE_NUMBER=""

# Callback events URI to handle callback events.
CALLBACK_URI_HOST = ""

CALLBACK_EVENTS_URI = CALLBACK_URI_HOST + "/api/callbacks"

TEMPLATE_FILES_PATH = "template"

BRING_YOUR_STORAGE_URL=""

IS_BYOS = False

IS_PAUSE_ON_START = False

HELLO_PROMPT = "Welcome to the Contoso Utilities. Thank you!"

call_automation_client = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)

app = Flask(__name__,
            template_folder=TEMPLATE_FILES_PATH)

@app.route('/createCall')
def outbound_call_handler():
    target_participant = CommunicationUserIdentifier(COMMUNICATION_USR_ID)
    # source_caller = PhoneNumberIdentifier(ACS_PHONE_NUMBER)
    call_connection_properties = call_automation_client.create_call(target_participant, 
                                                                    CALLBACK_URI_HOST,
                                                                    cognitive_services_endpoint=COGNITIVE_SERVICE_ENDPOINT
                                                                    )
    app.logger.info("Created call with connection id: %s", call_connection_properties.call_connection_id)
    return redirect("/")

def handle_recognize(replyText,callerId,call_connection_id,context=""):
    play_source = TextSource(text=replyText, voice_name="en-US-NancyNeural")    
    recognize_result=call_automation_client.get_call_connection(call_connection_id).start_recognizing_media( 
    input_type=RecognizeInputType.SPEECH,
    target_participant=PhoneNumberIdentifier(callerId), 
    end_silence_timeout=10, 
    play_prompt=play_source,
    operation_context=context)
    app.logger.info("handle_recognize : data=%s",recognize_result) 

def handle_play(call_connection_id, text_to_play, context):
    play_source = TextSource(text=text_to_play, voice_name= "en-US-NancyNeural") 
    call_automation_client.get_call_connection(call_connection_id).play_media_to_all(play_source,
                                                                                     operation_context=context)
    
def handle_hangup(call_connection_id):     
    call_automation_client.get_call_connection(call_connection_id).hang_up(is_for_everyone=True)
    
def start_recording(server_call_id):
     global recording_storage
     if IS_BYOS:
         recording_storage=AzureBlobContainerRecordingStorage(BRING_YOUR_STORAGE_URL)
     else:
         recording_storage=AzureCommunicationsRecordingStorage()
         
     recording_result = call_automation_client.start_recording(
                    call_locator=ServerCallLocator(server_call_id),
                    recording_content_type = RecordingContent.Audio,
                    recording_channel_type = RecordingChannel.Unmixed,
                    recording_format_type = RecordingFormat.Wav,
                    recording_storage= recording_storage,
                    pause_on_start = IS_PAUSE_ON_START
                    )
     global recording_id
     recording_id=recording_result.recording_id
     app.logger.info("Recording started...")
     app.logger.info("Recording Id --> %s", recording_id)
    
def get_recording_state(recordingId):
    recording_state_result = call_automation_client.get_recording_properties(recording_id)
    app.logger.info("Recording State --> %s", recording_state_result.recording_state)
    return recording_state_result.recording_state

@app.route("/api/incomingCall",  methods=['POST'])
def incoming_call_handler():
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

                answer_call_result = call_automation_client.answer_call(incoming_call_context=incoming_call_context,
                                                                        cognitive_services_endpoint=COGNITIVE_SERVICE_ENDPOINT,
                                                                        callback_url=callback_uri)
                app.logger.info("Answered call for connection id: %s",
                                answer_call_result.call_connection_id)
                return Response(status=200)
            
@app.route("/api/callbacks/<contextId>", methods=["POST"])
def handle_callback(contextId):    
    try:        
        global caller_id , call_connection_id, server_call_id
        # app.logger.info("Request Json: %s", request.json)
        for event_dict in request.json:       
            event = CloudEvent.from_dict(event_dict)
            call_connection_id = event.data['callConnectionId']
            
            app.logger.info("%s event received for call connection id: %s", event.type, call_connection_id)
            caller_id = request.args.get("callerId").strip()
            if "+" not in caller_id:
                caller_id="+".strip()+caller_id.strip()

            app.logger.info("call connected : data=%s", event.data)
            if event.type == "Microsoft.Communication.CallConnected":
                  app.logger.info("Call connected")
                  server_call_id = event.data["serverCallId"]
                  app.logger.info("Server Call Id --> %s", server_call_id)
                  app.logger.info("Is pause on start --> %s", IS_PAUSE_ON_START)
                  app.logger.info("Bring Your Own Storage --> %s", IS_BYOS)
                  if IS_BYOS:
                      app.logger.info("Bring Your Own Storage URL --> %s", BRING_YOUR_STORAGE_URL)
                  start_recording(server_call_id)
                  handle_play(call_connection_id,HELLO_PROMPT,"helloContext")
                 
            elif event.type == "Microsoft.Communication.RecognizeCompleted":
                 app.logger.info("Recognition completed")

            elif event.type == "Microsoft.Communication.RecognizeFailed":
                resultInformation = event.data['resultInformation']
                reasonCode = resultInformation['subCode']
                context=event.data['operationContext']   
            elif event.type == "Microsoft.Communication.PlayCompleted":
                context=event.data['operationContext']
                app.logger.info(context)
                
                recording_state = get_recording_state(recording_id)
                if recording_state == "active":
                    call_automation_client.pause_recording(recording_id)
                    time.sleep(5)
                    get_recording_state(recording_id)
                    app.logger.info("Recording is paused")
                    time.sleep(5)
                    call_automation_client.resume_recording(recording_id)
                    time.sleep(5)
                    get_recording_state(recording_id)
                    app.logger.info("Recording is resumed")
                else:
                    time.sleep(5)
                    call_automation_client.resume_recording(recording_id)
                    time.sleep(5)
                    get_recording_state(recording_id)
                time.sleep(5)
                call_automation_client.stop_recording(recording_id)
                app.logger.info("Recording is stopped")
                handle_hangup(call_connection_id)
            elif event.type == "Microsoft.Communication.CallTransferAccepted":
                app.logger.info(f"Call transfer accepted event received for connection id: {call_connection_id}")   
             
            elif event.type == "Microsoft.Communication.CallTransferFailed":
                app.logger.info(f"Call transfer failed event received for connection id: {call_connection_id}")
                resultInformation = event.data['resultInformation']
                sub_code = resultInformation['subCode']
                # check for message extraction and code
                app.logger.info(f"Encountered error during call transfer, message=, code=, subCode={sub_code}")   
            elif event.type == "Microsoft.Communication.CallDisconnected":             
                app.logger.info(f"Received CallDisconnected event for connection id: {call_connection_id}")
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
                global content_location, metadata_location, delete_location
                content_location = acs_recording_chunk_info_properties['contentLocation']
                metadata_location =  acs_recording_chunk_info_properties['metadataLocation']
                delete_location = acs_recording_chunk_info_properties['deleteLocation']
                app.logger.info("CONTENT LOCATION --> %s", content_location)
                app.logger.info("METADATA LOCATION --> %s", metadata_location)
                app.logger.info("DELETE LOCATION --> %s", delete_location)
                return Response(response="Ok")  
                                                  
    except Exception as ex:
         app.logger.error( "Failed to get recording file")
         return Response(response='Failed to get recording file', status=400)

@app.route('/download')
def download_recording():
        try:
            app.logger.info("Content location : %s", content_location)
            recording_data = call_automation_client.download_recording(content_location)
            with open("Recording_File.wav", "wb") as binary_file:
                binary_file.write(recording_data.read())
            return redirect("/")
        except Exception as ex:
            app.logger.info("Failed to download recording --> " + str(ex))
            return Response(text=str(ex), status=500)
        
@app.route('/downloadMetadata')
def download_metadata():
        try:
            app.logger.info("Content location : %s", content_location)
            recording_data = call_automation_client.download_recording(metadata_location)
            with open("Recording_metadata.json", "wb") as binary_file:
                binary_file.write(recording_data.read())
            return redirect("/")
        except Exception as ex:
            app.logger.info("Failed to download meatadata --> " + str(ex))
            return Response(text=str(ex), status=500)


# GET endpoint to render the menus
@app.route('/')
def index_handler():
    return render_template("index.html")

if __name__ == '__main__':
    app.logger.setLevel(INFO)
    app.run(port=8080)
