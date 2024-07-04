
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
    AzureCommunicationsRecordingStorage,
    RecognitionChoice,
    DtmfTone,
    FileSource
    )
from azure.core.messaging import CloudEvent

COMMUNICATION_USR_ID = ""

COMMUNICATION_USR_ID_2=""

# Your ACS resource connection string
ACS_CONNECTION_STRING = ""

# Cognitive service endpoint
COGNITIVE_SERVICE_ENDPOINT=""

# Agent Phone Number
TARGET_PHONE_NUMBER=""

TARGET_PHONE_NUMBER_2=""

ACS_PHONE_NUMBER=""

ACS_PHONE_NUMBER_2=""

# Callback events URI to handle callback events.
CALLBACK_URI_HOST = ""

CALLBACK_EVENTS_URI = CALLBACK_URI_HOST + "/api/callbacks"

TEMPLATE_FILES_PATH = "template"
AUDIO_FILES_PATH = "/audio"
MAIN_MENU_PROMPT_URI = CALLBACK_URI_HOST + AUDIO_FILES_PATH + "/MainMenu.wav"

BRING_YOUR_STORAGE_URL=""

IS_BYOS = False

IS_PAUSE_ON_START = False

IS_REJECT_CALL = False

IS_REDIRECT_CALL = False
 
IS_TRANSFER_CALL = False

IS_OUTBOUND_CALL = False

HELLO_PROMPT = "Welcome to the Contoso Utilities. Thank you!"

PSTN_USER_PROMPT = "Hello this is contoso recognition test please confirm or cancel to proceed further."

DTMF_PROMPT = "Thank you for the update. Please type  one two three four on your keypad to close call."

call_automation_client = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)

app = Flask(__name__,
            static_folder=AUDIO_FILES_PATH.strip("/"),
            static_url_path=AUDIO_FILES_PATH,
            template_folder=TEMPLATE_FILES_PATH)

@app.route('/createCall')
def create_call_handler():
    target_participant = CommunicationUserIdentifier(COMMUNICATION_USR_ID)
    # source_caller = PhoneNumberIdentifier(ACS_PHONE_NUMBER)
    call_connection_properties = call_automation_client.create_call(target_participant, 
                                                                    CALLBACK_URI_HOST,
                                                                    cognitive_services_endpoint=COGNITIVE_SERVICE_ENDPOINT
                                                                    )
    app.logger.info("Created call with connection id: %s", call_connection_properties.call_connection_id)
    return redirect("/")

@app.route('/createPstnCall')
def create_pstn_call():
     target_participant = PhoneNumberIdentifier(ACS_PHONE_NUMBER)
     source_caller = PhoneNumberIdentifier(ACS_PHONE_NUMBER_2)
     call_connection_properties = call_automation_client.create_call(target_participant,
                                                                     CALLBACK_EVENTS_URI,
                                                                     cognitive_services_endpoint=COGNITIVE_SERVICE_ENDPOINT,
                                                                     source_caller_id_number=source_caller)
     app.logger.info("Created pstn call with connection id: %s", call_connection_properties.call_connection_id)
     return redirect("/")

@app.route('/outboundCall')
def create_outbound_call():
    target_participant = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
    source_caller = PhoneNumberIdentifier(ACS_PHONE_NUMBER)
    call_connection_properties = call_automation_client.create_call(target_participant,
                                                                     CALLBACK_EVENTS_URI,
                                                                     cognitive_services_endpoint=COGNITIVE_SERVICE_ENDPOINT,
                                                                     source_caller_id_number=source_caller)
    app.logger.info("Created outbound call with connection id: %s", call_connection_properties.call_connection_id)
    return redirect("/")
@app.route('/createGroupCall')
def create_group_call():
    target_participant = CommunicationUserIdentifier(COMMUNICATION_USR_ID)
    target_participant_2 = CommunicationUserIdentifier(COMMUNICATION_USR_ID_2)
    pstn_participant1 = PhoneNumberIdentifier(ACS_PHONE_NUMBER_2)
    pstn_participant2 = PhoneNumberIdentifier(ACS_PHONE_NUMBER)
    call_connection_properties = call_automation_client.create_group_call([target_participant,target_participant_2,pstn_participant1,pstn_participant2],
                                                                     callback_url=CALLBACK_EVENTS_URI,
                                                                     cognitive_services_endpoint=COGNITIVE_SERVICE_ENDPOINT,
                                                                     source_caller_id_number=pstn_participant2
                                                                     )
    app.logger.info("Created group call with connection id: %s", call_connection_properties.call_connection_id)
    return redirect("/")

def handle_recognize(playText,callerId,call_connection_id,context="",isDtmf=False):
    choices = [ 
    RecognitionChoice( 
        label="Confirm", 
        phrases=[ "Confirm", "First", "One" ], 
        tone=DtmfTone.ONE 
    ), 
    RecognitionChoice( 
        label="Cancel", 
        phrases=[ "Cancel", "Second", "Two" ], 
        tone=DtmfTone.TWO 
    )] 

    if isDtmf:
        play_source = TextSource(text=playText, voice_name="en-US-NancyNeural")    
        recognize_result=call_automation_client.get_call_connection(call_connection_id).start_recognizing_media( 
        input_type=RecognizeInputType.DTMF,
        target_participant=PhoneNumberIdentifier(callerId), 
        end_silence_timeout=10,
        dtmf_max_tones_to_collect=4,
        play_prompt=play_source,
        operation_context=context)
    else:
        play_source = TextSource(text=playText, voice_name="en-US-NancyNeural")    
        recognize_result=call_automation_client.get_call_connection(call_connection_id).start_recognizing_media(
        input_type=RecognizeInputType.CHOICES,
        target_participant=PhoneNumberIdentifier(callerId),
        choices=choices, 
        end_silence_timeout=10, 
        play_prompt=play_source,
        operation_context=context)
        #SPEECH_OR_DTMF,SPEECH,CHOICES
def handle_play(call_connection_id, text_to_play, context):
    # play_source = TextSource(text=text_to_play, voice_name= "en-US-NancyNeural")
    play_source = FileSource(MAIN_MENU_PROMPT_URI)
    call_automation_client.get_call_connection(call_connection_id).play_media_to_all(play_source,
                                                                                     operation_context=context,
                                                                                     loop=False)
    # call_automation_client.get_call_connection(call_connection_id).play_media(play_source=play_source,
    #                                                                           play_to=PhoneNumberIdentifier(TARGET_PHONE_NUMBER),
    #                                                                           operation_context=context,
    #                                                                           loop=True)
    # time.sleep(5)
    # call_automation_client.get_call_connection(call_connection_id).cancel_all_media_operations()
    
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
                    recording_content_type = RecordingContent.AUDIO,
                    recording_channel_type = RecordingChannel.UNMIXED,
                    recording_format_type = RecordingFormat.WAV,
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

def start_continuous_dtmf(call_connection_id):
    call_automation_client.get_call_connection(call_connection_id).start_continuous_dtmf_recognition(target_participant=PhoneNumberIdentifier(TARGET_PHONE_NUMBER))
    app.logger.info("Continuous Dtmf recognition started. press 1 on dialpad.")

def stop_continuous_dtmf(call_connection_id):
    call_automation_client.get_call_connection(call_connection_id).stop_continuous_dtmf_recognition(target_participant=PhoneNumberIdentifier(TARGET_PHONE_NUMBER))
    app.logger.info("Continuous Dtmf recognition stopped. wait for sending dtmf tones.")

def start_send_dtmf_tones(call_connection_id):
    tones = [DtmfTone.ONE,DtmfTone.TWO]
    call_automation_client.get_call_connection(call_connection_id).send_dtmf_tones(tones=tones,
                                           target_participant=PhoneNumberIdentifier(TARGET_PHONE_NUMBER))
    app.logger.info("Send dtmf tone started.")

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
                
                if IS_REJECT_CALL:
                    app.logger.info("Is Reject Call: %s",  IS_REJECT_CALL)
                    call_automation_client.reject_call(incoming_call_context=incoming_call_context)
                    app.logger.info(f"Call Rejected, recject call setting is {IS_REJECT_CALL}")
                elif IS_REDIRECT_CALL:
                    app.logger.info("Is Redirect Call: %s",  IS_REDIRECT_CALL)
                    call_automation_client.redirect_call(incoming_call_context=incoming_call_context,
                                                         target_participant=PhoneNumberIdentifier(TARGET_PHONE_NUMBER))
                    app.logger.info("Call redirected. Call automation has no control.")
                else:
                    answer_call_result = call_automation_client.answer_call(incoming_call_context=incoming_call_context,
                                                                        cognitive_services_endpoint=COGNITIVE_SERVICE_ENDPOINT,
                                                                        callback_url=callback_uri)
                    app.logger.info("Answered call for connection id: %s",
                                answer_call_result.call_connection_id)
                return Response(status=200)
# For outbound call.
# @app.route('/api/callbacks', methods=['POST'])
# def handle_callback():        
@app.route("/api/callbacks/<contextId>", methods=["POST"])
def handle_callback(contextId):
    try:        
        global caller_id , call_connection_id, server_call_id,call_connection_client,cor_relation_id
        # app.logger.info("Request Json: %s", request.json)
        for event_dict in request.json:       
            event = CloudEvent.from_dict(event_dict)
            call_connection_id = event.data['callConnectionId']
            cor_relation_id = event.data['correlationId']
            app.logger.info(f"***CALLCONNECTIONID*** ->  {call_connection_id}")
            app.logger.info(f"***CORRELATIONID*** -> {cor_relation_id}")
            app.logger.info("%s event received for call connection id: %s", event.type, call_connection_id)
            app.logger.info("call connected : data=%s", event.data)
            if event.type == "Microsoft.Communication.CallConnected":
                  app.logger.info("Call connected")
                  server_call_id = event.data["serverCallId"]
                  app.logger.info("Server Call Id --> %s", server_call_id)
                  app.logger.info("Is pause on start --> %s", IS_PAUSE_ON_START)
                  app.logger.info("Bring Your Own Storage --> %s", IS_BYOS)
                  call_connection_client =call_automation_client.get_call_connection(call_connection_id=call_connection_id)
                  
                #   call_connection_properties = call_connection_client.get_call_properties()
                #   app.logger.info("ANSWERED FOR --> %s", call_connection_properties.answered_for.raw_id)
                  if IS_BYOS:
                      app.logger.info("Bring Your Own Storage URL --> %s", BRING_YOUR_STORAGE_URL)
                 
                  if IS_TRANSFER_CALL:
                      app.logger.info("Is Transfer Call:--> %s", IS_TRANSFER_CALL)
                      call_connection_client.transfer_call_to_participant(
                          target_participant=PhoneNumberIdentifier(TARGET_PHONE_NUMBER),
                          transferee=PhoneNumberIdentifier(ACS_PHONE_NUMBER_2),
                          source_caller_id_number=PhoneNumberIdentifier(ACS_PHONE_NUMBER))
                      app.logger.info("Transfer call initiated.")
                      return 
                  elif IS_OUTBOUND_CALL:
                      app.logger.info("Is Outbound Call:--> %s", IS_OUTBOUND_CALL)
                      app.logger.info("Outbound call connected.")
                      
                      # Cancel add participant test.
                    #   app.logger.info("Cancel add participant test initiated.")
                    #   response = call_connection_client.add_participant(target_participant=PhoneNumberIdentifier(ACS_PHONE_NUMBER_2),
                    #                                      source_caller_id_number=PhoneNumberIdentifier(ACS_PHONE_NUMBER),
                    #                                      invitation_timeout=10
                    #                                      )
                    #   app.logger.info(f"Invitation Id:--> {response.invitation_id}")   
                    #   call_connection_client.cancel_add_participant_operation(response.invitation_id
                    #                                                         #   operation_context="cancelAddParticipantContext"
                    #                                                         )
                      # Cancel add participant test end
                      
                      # Transfer call test
                    #   call_connection_client.transfer_call_to_participant(target_participant=PhoneNumberIdentifier(TARGET_PHONE_NUMBER_2),
                    #                                                       transferee=PhoneNumberIdentifier(TARGET_PHONE_NUMBER),
                    #                                                       operation_context="transferCallContext")
                    #   app.logger.info("Transfer call initiated.")
                      # Transfer call test end.
                      
                    #   start_continuous_dtmf(call_connection_id=call_connection_id)
                      
                    #   handle_play(call_connection_id,"this is loop test","outboundPlayContext")
                      
                    #   handle_hangup(call_connection_id)
                      call_automation_client.get_call_connection(call_connection_id).hang_up(is_for_everyone=False)
                  else:
                      start_recording(server_call_id)
                      
                      call_connection_client.add_participant(target_participant=PhoneNumberIdentifier(TARGET_PHONE_NUMBER),
                                                             source_caller_id_number=PhoneNumberIdentifier(ACS_PHONE_NUMBER),
                                                             operation_context="addPstnUserContext",
                                                             invitation_timeout=10)
                      app.logger.info("Adding PSTN participant")
                 
            elif event.type == "Microsoft.Communication.RecognizeCompleted":
                 app.logger.info("Recognition completed")
                 app.logger.info("Recognize completed: data=%s", event.data) 
                 if event.data['recognitionType'] == "dtmf": 
                    tones = event.data['dtmfResult']['tones'] 
                    app.logger.info("Recognition completed, tones=%s, context=%s", tones, event.data.get('operationContext'))
                    call_connection_client.remove_participant(target_participant=PhoneNumberIdentifier(TARGET_PHONE_NUMBER))
                 elif event.data['recognitionType'] == "choices": 
                    labelDetected = event.data['choiceResult']['label']; 
                    phraseDetected = event.data['choiceResult']['recognizedPhrase']; 
                    app.logger.info("Recognition completed, labelDetected=%s, phraseDetected=%s, context=%s", labelDetected, phraseDetected, event.data.get('operationContext'));
                    if  labelDetected == "Confirm":
                        app.logger.info("Moving towords dtmf test.")
                        handle_recognize(playText=DTMF_PROMPT,
                                         callerId=TARGET_PHONE_NUMBER,
                                         call_connection_id=call_connection_id,
                                         context="recognizeDtmfContext",isDtmf=True)
                    else:
                        app.logger.info("Moving towords continuous dtmf & send dtmf tones test.")
                        start_continuous_dtmf(call_connection_id=call_connection_id)
                 elif event.data['recognitionType'] == "speech": 
                    text = event.data['speechResult']['speech']; 
                    app.logger.info("Recognition completed, text=%s, context=%s", text, event.data.get('operationContext'))
                    handle_hangup(call_connection_id=call_connection_id)
                 else: 
                    app.logger.info("Recognition completed: data=%s", event.data); 
                 
            elif event.type == "Microsoft.Communication.RecognizeFailed":
                resultInformation = event.data['resultInformation']
                reasonCode = resultInformation['subCode']
                context=event.data['operationContext']
                handle_recognize(playText="test",
                                         callerId=TARGET_PHONE_NUMBER,
                                         call_connection_id=call_connection_id,
                                         context="retryRecognizeContext",isDtmf=False)
                app.logger.info("Cancelling all media operations.")
                call_automation_client.get_call_connection(call_connection_id).cancel_all_media_operations()
                app.logger.info("cancel add participant test initiated.")
                response = call_connection_client.add_participant(target_participant=PhoneNumberIdentifier(ACS_PHONE_NUMBER_2),
                                                         source_caller_id_number=PhoneNumberIdentifier(ACS_PHONE_NUMBER),
                                                         invitation_timeout=10)
                app.logger.info(f"Invitation Id:--> {response.invitation_id}")   
                call_connection_client.cancel_add_participant_operation(response.invitation_id)
            elif event.type == "Microsoft.Communication.PlayCompleted":
                context=event.data['operationContext']
                app.logger.info(context)
                if context == "outboundPlayContext":
                    handle_hangup(call_connection_id=call_connection_id)
                    return
                if context == "continuousDtmfPlayContext":
                    app.logger.info("test")
                    return
                
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
                    call_automation_client.pause_recording(recording_id)
                    time.sleep(5)
                    get_recording_state(recording_id)
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
                app.logger.info(f"Operation context:--> {event.data['operationContext']}")
            elif event.type == "Microsoft.Communication.CallTransferFailed":
                app.logger.info(f"Call transfer failed event received for connection id: {call_connection_id}")
                resultInformation = event.data['resultInformation']
                sub_code = resultInformation['subCode']
                
                app.logger.info(f"Encountered error during call transfer, message=, code=, subCode={sub_code}")
                
            elif event.type == "Microsoft.Communication.AddParticipantSucceeded":
                app.logger.info(f"Received AddParticipantSucceeded event for connection id: {call_connection_id}")
                if(event.data['operationContext'] == "addPstnUserContext"):
                    app.logger.info("PSTN user added")
                    participants = call_connection_client.list_participants()
                    app.logger.info("Listing participants in call...")
                    for page in participants.by_page():
                        for participant in page:
                             app.logger.info("Participant: %s", participant.identifier.raw_id)
                    mute_result = call_connection_client.mute_participant(CommunicationUserIdentifier(COMMUNICATION_USR_ID))
                    if mute_result:
                        app.logger.info("Participant is muted. wating for confirming.....")
                        time.sleep(5)
                        response = call_connection_client.get_participant(CommunicationUserIdentifier(COMMUNICATION_USR_ID))
                        if response:
                            app.logger.info(f"Is participant muted: {response.is_muted}")
                            app.logger.info("Mute participant test completed.")
                    
                    handle_recognize(playText=PSTN_USER_PROMPT,
                                     callerId=TARGET_PHONE_NUMBER,
                                     call_connection_id=call_connection_id,
                                     context="recognizeContext",isDtmf=False)
                    
                    # handle_play(call_connection_id,HELLO_PROMPT,"helloContext")
                    
            elif event.type == "Microsoft.Communication.AddParticipantFailed":
                app.logger.info(f"AddParticipantFailed event received for connection id: {call_connection_id}")
                resultInformation = event.data['resultInformation']
                sub_code = resultInformation['subCode']
                handle_hangup(call_connection_id)
            elif event.type == "Microsoft.Communication.CancelAddParticipantSucceeded":
                app.logger.info(f"Received CancelAddParticipantSucceeded event for connection id: {call_connection_id}")
                app.logger.info(f"Invitation Id:--> {event.data['invitationId']}")
                # app.logger.info(f"Operation context:--> {event.data['operationContext']}")
                app.logger.info("Cancel add participant test completed.")
                handle_hangup(call_connection_id)
            elif event.type == "Microsoft.Communication.CancelAddParticipantFailed":
                app.logger.info(f"Received CancelAddParticipantFailed event for connection id: {call_connection_id}")
                resultInformation = event.data['resultInformation']
                sub_code = resultInformation['subCode']
                app.logger.info(f"Result Information:--> {resultInformation}")
                app.logger.info(f"Sub code:--> {sub_code}")
                handle_hangup(call_connection_id)
            elif event.type == "Microsoft.Communication.ContinuousDtmfRecognitionToneReceived":
                app.logger.info(f"Received ContinuousDtmfRecognitionToneReceived event for connection id: {call_connection_id}")
                app.logger.info(f"Tone received:-->: {event.data['tone']}")
                app.logger.info(f"Sequence Id:--> {event.data['sequenceId']}")
                #handle_play(call_connection_id,HELLO_PROMPT,"continuousDtmfPlayContext")
                stop_continuous_dtmf(call_connection_id=call_connection_id)
            elif event.type == "Microsoft.Communication.ContinuousDtmfRecognitionToneFailed":
                app.logger.info(f"Received ContinuousDtmfRecognitionToneFailed event for connection id: {call_connection_id}")
                resultInformation = event.data['resultInformation']
                sub_code = resultInformation['subCode']
                handle_hangup(call_connection_id)
            elif event.type == "Microsoft.Communication.ContinuousDtmfRecognitionStopped":
                app.logger.info(f"Received ContinuousDtmfRecognitionStopped event for connection id: {call_connection_id}")
                start_send_dtmf_tones(call_connection_id=call_connection_id)
            elif event.type == "Microsoft.Communication.SendDtmfTonesCompleted":
                app.logger.info(f"Received SendDtmfTonesCompleted event for connection id: {call_connection_id}")
                call_connection_client.remove_participant(target_participant=PhoneNumberIdentifier(TARGET_PHONE_NUMBER))
                app.logger.info(f"Send Dtmf tone completed. {TARGET_PHONE_NUMBER} will be removed from call.")                       
            elif event.type == "Microsoft.Communication.SendDtmfTonesFailed":
                app.logger.info(f"Received SendDtmfTonesFailed event for connection id: {call_connection_id}")
                resultInformation = event.data['resultInformation']
                sub_code = resultInformation['subCode']
            elif event.type == "Microsoft.Communication.RemoveParticipantSucceeded":
                app.logger.info(f"Received RemoveParticipantSucceeded event for connection id: {call_connection_id}")
                handle_play(call_connection_id,HELLO_PROMPT,"helloContext")
            elif event.type == "Microsoft.Communication.RemoveParticipantFailed":
                app.logger.info(f"Received RemoveParticipantFailed event for connection id: {call_connection_id}")
                resultInformation = event.data['resultInformation']
                sub_code = resultInformation['subCode']
            elif event.type == "Microsoft.Communication.RecordingStateChanged":             
                app.logger.info(f"Received RecordingStateChanged event for connection id: {call_connection_id}")   
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
            app.logger.info("Metadata location : %s", metadata_location)
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
