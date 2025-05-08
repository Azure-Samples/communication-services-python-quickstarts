from azure.eventgrid import EventGridEvent, SystemEventNames
from quart import Quart, Response, request, json, send_file, render_template, redirect
from logging import INFO
import time
import json
from azure.communication.callautomation import (
    CallAutomationClient,
    CallConnectionClient,
    PhoneNumberIdentifier,
    CommunicationUserIdentifier,
    RecognizeInputType,
    MicrosoftTeamsUserIdentifier,
    CallInvite,
    RecognitionChoice,
    DtmfTone,
    TextSource,
    # RoomCallLocator,
    GroupCallLocator,
    ServerCallLocator,
    RecordingContent,
    RecordingChannel,
    RecordingFormat,
    FileSource,
    SsmlSource,
    AzureBlobContainerRecordingStorage,
    AzureCommunicationsRecordingStorage,
    AddParticipantResult,
    CommunicationIdentifier
    # MediaStreamingOptions,
    # MediaStreamingTransportType,
    # MediaStreamingContentType,
    # MediaStreamingAudioChannelType,
    # TranscriptionOptions,
    # TranscriptionTransportType
    )
from azure.communication.callautomation.aio import (
    CallAutomationClient
    )
from azure.core.messaging import CloudEvent

# Your ACS resource connection string
ACS_CONNECTION_STRING = "endpoint=https://dacsrecordingtest.unitedstates.communication.azure.com/;accesskey=FWMCjVWSbPyivHtGZ3Kph0XKvbMowgHoWYekUDXcfZhzrVdc0l1gJQQJ99ALACULyCpAArohAAAAAZCSNRZe"

# Your ACS resource phone number will act as source number to start outbound call
ACS_PHONE_NUMBER = "+18332638155"

# Target phone number you want to receive the call.
TARGET_PHONE_NUMBER = "+918983968975"

PARTICIPANT_PHONE_NUMBER = "+918983968975"

TARGET_COMMUNICATION_USER="8:acs:19ae37ff-1a44-4e19-aade-198eedddbdf2_00000023-a9cc-6d8c-ec8d-084822001d42"
 
PARTICIPANT_COMMUNICATION_USER="8:acs:19ae37ff-1a44-4e19-aade-198eedddbdf2_00000023-a9cc-6d8c-ec8d-084822001d42"

# Callback events URI to handle callback events.
CALLBACK_URI_HOST = "https://239e-182-156-148-150.ngrok-free.app"
CALLBACK_EVENTS_URI = CALLBACK_URI_HOST + "/api/callbacks"
COGNITIVE_SERVICES_ENDPOINT = "https://cognitive-service-waferwire.cognitiveservices.azure.com/"

#(OPTIONAL) Your target Microsoft Teams user Id ex. "ab01bc12-d457-4995-a27b-c405ecfe4870"
TARGET_TEAMS_USER_ID = "<TARGET_TEAMS_USER_ID>"

TEMPLATE_FILES_PATH = "template"

BRING_YOUR_OWN_STORAGE_URL=""
IS_BYOS=False
IS_PAUSE_ON_START=False
BRING_YOUR_STORAGE_URL=""
TRANSPORT_URL=""

# Prompts for text to speech

CONFIRM_CHOICE_LABEL = "Confirm"
CANCEL_CHOICE_LABEL = "Cancel"
RETRY_CONTEXT = "retry"
AUDIO_FILES_PATH = "/audio"
MAIN_MENU_PROMPT_URI = CALLBACK_URI_HOST + AUDIO_FILES_PATH + "/MainMenu.wav"

RECOGNITION_PROMPT = "Hello this is contoso recognition test please confirm or cancel to proceed further."
PLAY_PROMPT = "Welcome to the Contoso Utilities. Thank you!"
SSML_PLAY_TEXT = "<speak version=\"1.0\" xmlns=\"http://www.w3.org/2001/10/synthesis\" xml:lang=\"en-US\"><voice name=\"en-US-JennyNeural\">Welcome to the Contoso Utilities. Played through SSML. Thank you!</voice></speak>"
SSML_RECOGNITION_TEXT = "<speak version=\"1.0\" xmlns=\"http://www.w3.org/2001/10/synthesis\" xml:lang=\"en-US\"><voice name=\"en-US-JennyNeural\">Hello this is SSML recognition test please confirm or cancel to proceed further. Thank you!</voice></speak>"
HOLD_PROMPT = "You are on hold please wait."
SSML_HOLD_TEXT = "<speak version=\"1.0\" xmlns=\"http://www.w3.org/2001/10/synthesis\" xml:lang=\"en-US\"><voice name=\"en-US-JennyNeural\">You are on hold please wait. Played through SSML. Thank you!</voice></speak>"
INTERRUPT_PROMPT = "Play is interrupted."
SSML_INTERRUPT_TEXT = "<speak version=\"1.0\" xmlns=\"http://www.w3.org/2001/10/synthesis\" xml:lang=\"en-US\"><voice name=\"en-US-JennyNeural\">Play is interrupted. Played through SSML. Thank you!</voice></speak>"

call_automation_client = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)

app = Quart(__name__,
            static_folder=AUDIO_FILES_PATH.strip("/"),
            static_url_path=AUDIO_FILES_PATH,
            template_folder=TEMPLATE_FILES_PATH)

async def create_call():

    is_acs_user_target = False 

    # media_streaming_options = MediaStreamingOptions(
    #     transport_url=TRANSPORT_URL,
    #     transport_type=MediaStreamingTransportType.WEBSOCKET,
    #     content_type=MediaStreamingContentType.AUDIO,
    #     audio_channel_type=MediaStreamingAudioChannelType.UNMIXED,
    #     start_media_streaming=False
    #     )
    
    # transcription_options = TranscriptionOptions(
    #     transport_url=TRANSPORT_URL,
    #     transport_type=TranscriptionTransportType.WEBSOCKET,
    #     locale="en-US",
    #     start_transcription=False
    #     )

    if is_acs_user_target:
        acs_target = CommunicationUserIdentifier(TARGET_COMMUNICATION_USER)
        call_connection_properties = await call_automation_client.create_call(
            acs_target, 
            CALLBACK_EVENTS_URI,
            cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT,
            # media_streaming=media_streaming_options,
            # transcription=transcription_options
            )
    else:     
        pstn_target = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
        source_caller = PhoneNumberIdentifier(ACS_PHONE_NUMBER)
        call_connection_properties = await call_automation_client.create_call(
            pstn_target, 
            CALLBACK_EVENTS_URI,
            cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT,
            source_caller_id_number=source_caller,
            # media_streaming=media_streaming_options,
            # transcription=transcription_options
            )
        
    app.logger.info("Created call with Correlation id: - %s", call_connection_properties.correlation_id)

async def create_group_call():
     acs_target = CommunicationUserIdentifier(TARGET_COMMUNICATION_USER)
     pstn_target = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
     source_caller = PhoneNumberIdentifier(ACS_PHONE_NUMBER)
     targets = [pstn_target,acs_target]
     
    #  media_streaming_options = MediaStreamingOptions(
    #     transport_url=TRANSPORT_URL,
    #     transport_type=MediaStreamingTransportType.WEBSOCKET,
    #     content_type=MediaStreamingContentType.AUDIO,
    #     audio_channel_type=MediaStreamingAudioChannelType.UNMIXED,
    #     start_media_streaming=False
    #     )
    
    #  transcription_options = TranscriptionOptions(
    #     transport_url=TRANSPORT_URL,
    #     transport_type=TranscriptionTransportType.WEBSOCKET,
    #     locale="en-US",
    #     start_transcription=False
    #     )
     
     call_connection_properties = await call_automation_client.create_call(
            targets, 
            CALLBACK_EVENTS_URI,
            cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT,
            source_caller_id_number=source_caller,
            # media_streaming=media_streaming_options,
            # transcription=transcription_options
            )
     app.logger.info("Created group call with connection id: %s", call_connection_properties.call_connection_id)

async def connect_call():
    # call_automation_client.connect_call(
    #     room_id="",
    #     callback_url=CALLBACK_EVENTS_URI,
    #     cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT,
    #     operation_context="connectCallContext")
    
    await call_automation_client.connect_call(
        group_call_id="593c4e2a-c1c7-4863-9b7e-64b984cbc362",
        callback_url=CALLBACK_EVENTS_URI,
        # cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT,
        backup_cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT,
        operation_context="connectCallContext")
    
    # await call_automation_client.connect_call(
    #     server_call_id="",
    #     callback_url=CALLBACK_EVENTS_URI,
    #     cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT,
    #     operation_context="connectCallContext")

def get_choices():
    choices = [
                RecognitionChoice(label = CONFIRM_CHOICE_LABEL, phrases= ["Confirm", "First", "One"], tone = DtmfTone.ONE),
                RecognitionChoice(label = CANCEL_CHOICE_LABEL, phrases= ["Cancel", "Second", "Two"], tone = DtmfTone.TWO)
            ]
    return choices

async def play_recognize():
     
    text_source = TextSource(text=RECOGNITION_PROMPT, voice_name="en-US-NancyNeural")
    file_source = FileSource(url=MAIN_MENU_PROMPT_URI)
    ssml_text = SsmlSource(ssml_text=SSML_RECOGNITION_TEXT)
    play_sources = [text_source,file_source,ssml_text]
    target = get_communication_target()
     
    await call_automation_client.get_call_connection(call_connection_id).start_recognizing_media(
                input_type=RecognizeInputType.CHOICES,
                target_participant=target,
                choices=get_choices(),
                play_prompt=text_source,
                interrupt_prompt=False,
                initial_silence_timeout=10,
                operation_context="choiceContext")
     
    # await call_automation_client.get_call_connection(call_connection_id).start_recognizing_media(
    #             input_type=RecognizeInputType.DTMF,
    #             target_participant=target,
    #             # play_prompt=text_source,
    #             play_prompt=text_source,
    #             dtmf_max_tones_to_collect=1,
    #             interrupt_prompt=False,
    #             initial_silence_timeout=10,
    #             operation_context="dtmfContext"
    #         )
     
    # await call_automation_client.get_call_connection(call_connection_id).start_recognizing_media( 
    #             input_type=RecognizeInputType.SPEECH, 
    #             target_participant=target, 
    #             end_silence_timeout=10, 
    #             play_prompt=text_source, 
    #             operation_context="OpenQuestionSpeech")
     
    # await call_automation_client.get_call_connection(call_connection_id).start_recognizing_media( 
    #             dtmf_max_tones_to_collect=1, 
    #             input_type=RecognizeInputType.SPEECH_OR_DTMF, 
    #             target_participant=target, 
    #             end_silence_timeout=10, 
    #             play_prompt=text_source, 
    #             initial_silence_timeout=30, 
    #             interrupt_prompt=True, 
    #             operation_context="OpenQuestionSpeechOrDtmf")
     
async def play_media():
     is_play_to_all = True
     
     text_source = TextSource(text=PLAY_PROMPT, voice_name="en-US-NancyNeural")
     file_source = FileSource(url=MAIN_MENU_PROMPT_URI)
     ssml_text = SsmlSource(ssml_text=SSML_PLAY_TEXT)
     
     target = get_communication_target()
     play_sources = [file_source]
    #  play_sources = [text_source,file_source,ssml_text]
    #  play_sources = [text_source,file_source,ssml_text,text_source,file_source,ssml_text,text_source,file_source,ssml_text,text_source]
     
     if(is_play_to_all):
          await call_automation_client.get_call_connection(call_connection_id).play_media_to_all(
               play_source=play_sources,
               operation_context="playToAllContext",
               loop=False,
               operation_callback_url=CALLBACK_EVENTS_URI,
               interrupt_call_media_operation=False
               )
     else:
          await call_automation_client.get_call_connection(call_connection_id).play_media(
               play_source=play_sources)
            #    play_to=[target],
            #    operation_context="playToContext",
            #    loop=False,
            #    operation_callback_url=CALLBACK_EVENTS_URI,
            #    interrupt_call_media_operation=False
            # )
    

async def start_continuous_dtmf():
    target = get_communication_target()
    await call_automation_client.get_call_connection(call_connection_id).start_continuous_dtmf_recognition(target_participant=target)
    app.logger.info("Continuous Dtmf recognition started. press 1 on dialpad.")

async def stop_continuous_dtmf():
    target = get_communication_target()
    await call_automation_client.get_call_connection(call_connection_id).stop_continuous_dtmf_recognition(target_participant=target)
    app.logger.info("Continuous Dtmf recognition stopped.")

async def start_send_dtmf_tones():
    target = get_communication_target()
    tones = [DtmfTone.ONE,DtmfTone.TWO]
    await call_automation_client.get_call_connection(call_connection_id).send_dtmf_tones(tones=tones,target_participant=target)
    app.logger.info("Send dtmf tone started.")

async def start_recording():
     global recording_storage
     if IS_BYOS:
         recording_storage=AzureBlobContainerRecordingStorage(BRING_YOUR_STORAGE_URL)
     else:
         recording_storage=AzureCommunicationsRecordingStorage()
         
     properties = await get_call_properties()
     server_call_id = properties.server_call_id
     
     recording_result = await call_automation_client.start_recording(
                    call_locator=ServerCallLocator(server_call_id),
                    recording_content_type = RecordingContent.AUDIO,
                    recording_channel_type = RecordingChannel.UNMIXED,
                    recording_format_type = RecordingFormat.WAV,
                    recording_storage= recording_storage,
                    pause_on_start = IS_PAUSE_ON_START,
                    recording_state_callback_url=CALLBACK_EVENTS_URI
                    )
     global recording_id
     recording_id=recording_result.recording_id
     app.logger.info("Recording started...")
     app.logger.info("Recording Id --> %s", recording_id)
     
async def pause_recording():
     if recording_id:
          if(get_recording_state() == "active"):
               await call_automation_client.pause_recording(recording_id)
               app.logger.info("Recoriding is paused.")
          else:
               app.logger.info("Recording is already inactive.")
     else:
          app.logger.info("Recording id is empty.")
          
async def resume_recording():
     if recording_id:
          if(get_recording_state() == "inactive"):
               await call_automation_client.resume_recording(recording_id)
               app.logger.info("Recoriding is resumed.")
          else:
               app.logger.info("Recording is already active.")
     else:
          app.logger.info("Recording id is empty.")
               
async def stop_recording():
     if recording_id:
          if(get_recording_state() == "active"):
               await call_automation_client.resume_recording(recording_id)
               app.logger.info("Recording is stopped.")
          else:
               app.logger.info("Recording is already inactive.")
     else:
          app.logger.info("Recording id is empty.")

async def get_recording_state():
    recording_state_result = await call_automation_client.get_recording_properties(recording_id)
    app.logger.info("Recording State --> %s", recording_state_result.recording_state)
    return recording_state_result.recording_state

async def add_participant():
    is_cancel_add_participant = False
    is_acs_user_participant = False
    
    add_participant_result:AddParticipantResult = None
    
    if(is_acs_user_participant):
        add_participant_result = await call_automation_client.get_call_connection(call_connection_id).add_participant(
            target_participant=CommunicationUserIdentifier(PARTICIPANT_COMMUNICATION_USER),
            operation_context="addAcsUserContext",
            invitation_timeout=30)
    else:
         add_participant_result = await call_automation_client.get_call_connection(call_connection_id).add_participant(
            target_participant=PhoneNumberIdentifier(PARTICIPANT_PHONE_NUMBER),
            operation_context="addPstnUserContext",
            source_caller_id_number=PhoneNumberIdentifier(ACS_PHONE_NUMBER),
            invitation_timeout=30)
     
    if(is_cancel_add_participant):
         call_automation_client.get_call_connection(call_connection_id).cancel_add_participant_operation(add_participant_result.invitation_id)
         
async def remove_participant():
    target = get_communication_target()
    await call_automation_client.get_call_connection(call_connection_id).remove_participant(
        target_participant=target,
        operation_context="removeParticipantContext")
    
async def cancel_all_media_oparation():
    await call_automation_client.get_call_connection(call_connection_id).cancel_all_media_operations()

async def transfer_call_to_participant():
     
    is_acs_participant = False
    
    transfer_target = CommunicationUserIdentifier(PARTICIPANT_COMMUNICATION_USER) if is_acs_participant else PhoneNumberIdentifier(PARTICIPANT_PHONE_NUMBER)
    app.logger.info("Transfer target:- %s", transfer_target.raw_id)
    await call_automation_client.get_call_connection(call_connection_id).transfer_call_to_participant(
         target_participant=transfer_target,
         operation_context="transferCallContext",
         transferee=PhoneNumberIdentifier(TARGET_PHONE_NUMBER),
         source_caller_id_number=PhoneNumberIdentifier(ACS_PHONE_NUMBER)
         )
    app.logger.info("Transfer call initiated.")

# def start_media_streaming():
#      call_automation_client.get_call_connection(call_connection_id).start_media_streaming(
#         operation_callback_url=CALLBACK_EVENTS_URI,
#         operation_context="startMediaStreamingContext")

# def stop_media_streaming():
#     call_automation_client.get_call_connection(call_connection_id).stop_media_streaming(
#     operation_callback_url=CALLBACK_EVENTS_URI,
#     operation_context="stopMediaStreamingContext")
     
# def start_transcription():
#     call_automation_client.get_call_connection(call_connection_id).start_transcription(
#     locale="en-us",
#     operation_context="startTranscriptionContext")
    
# def update_transcription():
#     call_automation_client.get_call_connection(call_connection_id).update_transcription(
#     locale="en-au",
#     operation_context="updateTranscriptionContext")
    
# def stop_transcription():
#     call_automation_client.get_call_connection(call_connection_id).stop_transcription(
#     operation_context="stopTranscriptionContext")
    
async def hold_participant():
    
    text_source = TextSource(text=HOLD_PROMPT, voice_name="en-US-NancyNeural")
    file_source = FileSource(url=MAIN_MENU_PROMPT_URI)
    ssml_text = SsmlSource(ssml_text=SSML_HOLD_TEXT)
     
    target = get_communication_target()
    await call_automation_client.get_call_connection(call_connection_id).hold(
    target_participant=target,
    play_source=text_source,
    # operation_context="holdUserContext"
    )
    
    time.sleep(5)
    
    result = await get_participant(target)
    app.logger.info("Participant:--> %s",result.identifier.raw_id)
    app.logger.info("Is participant on hold:--> %s",result.is_on_hold)

    
async def unhold_participant():
    target = get_communication_target()
    await call_automation_client.get_call_connection(call_connection_id).unhold(
    target_participant=target
    # operation_context="unholdUserContext"
    )
     
    time.sleep(5)
    
    result = await get_participant(target)
    app.logger.info("Participant:--> %s",result.identifier.raw_id)
    app.logger.info("Is participant on hold:--> %s",result.is_on_hold)

    
async def play_with_interrupt_media_flag():
    text_source = TextSource(text=INTERRUPT_PROMPT, voice_name="en-US-NancyNeural")
    file_source = FileSource(url=MAIN_MENU_PROMPT_URI)
    ssml_text = SsmlSource(ssml_text=SSML_INTERRUPT_TEXT)
    
    # play_sources = [text_source]
    play_sources = [text_source,file_source,ssml_text]
    call_connection = call_automation_client.get_call_connection(call_connection_id)
    await call_connection.play_media_to_all(
    play_source=play_sources,
    loop=False,
    operation_context="interruptMediaContext",
    operation_callback_url=CALLBACK_EVENTS_URI,
    interrupt_call_media_operation=True)
    
async def mute_participant():
    target = get_communication_target()
    await call_automation_client.get_call_connection(call_connection_id).mute_participant(
    target_participant=target,
    operation_context="muteParticipantContext")
    
    time.sleep(5)
    
    result = await get_participant(target)
    app.logger.info("Participant:--> %s",result.identifier.raw_id)
    app.logger.info("Is participant muted:--> %s",result.is_muted)
    
async def get_participant(target:CommunicationIdentifier):
    participant =  await call_automation_client.get_call_connection(call_connection_id).get_participant(target)
    return participant
    
async def get_participant_list():
    participants = call_automation_client.get_call_connection(call_connection_id).list_participants()
    app.logger.info("Listing participants in call")
    async for page in participants.by_page():
        async for participant in page:
            app.logger.info("-------------------------------------------------------------")
            app.logger.info("Participant: %s", participant.identifier.raw_id)
            app.logger.info("Is participant muted: %s", participant.is_muted)
            app.logger.info("Is participant on hold: %s", participant.is_on_hold)
            app.logger.info("-------------------------------------------------------------")    

async def hangup_call():
    await call_automation_client.get_call_connection(call_connection_id).hang_up(False)
    
async def terminate_call():
    await call_automation_client.get_call_connection(call_connection_id).hang_up(True)

def get_communication_target():
     is_pstn_participant = False
     is_acs_participant = False
     is_acs_user = False
     
     pstn_identifier = PhoneNumberIdentifier(PARTICIPANT_PHONE_NUMBER) if is_pstn_participant else PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
     acs_identifier = CommunicationUserIdentifier(PARTICIPANT_COMMUNICATION_USER) if is_acs_participant else CommunicationUserIdentifier(TARGET_COMMUNICATION_USER)
     target = acs_identifier if is_acs_user else pstn_identifier
     app.logger.info("###############TARGET############---> %s", target.raw_id)
     return target

async def get_call_properties():
     call_properties = await call_automation_client.get_call_connection(call_connection_id).get_call_properties()
     return call_properties

# POST endpoint to handle callback events
@app.route('/api/callbacks', methods=['POST'])
async def callback_events_handler():
    for event_dict in await request.json:
        # Parsing callback events
        event = CloudEvent.from_dict(event_dict)
        global call_connection_id
        call_connection_id = event.data['callConnectionId']
        app.logger.info("%s event received for call correlation id: %s", event.type, event.data['callConnectionId'] )
        call_connection_client = call_automation_client.get_call_connection(call_connection_id)
        
        if event.type == "Microsoft.Communication.CallConnected":
            app.logger.info(f"Received CallConnected event for connection id: {event.data["callConnectionId"]}")
            call_connection_id = event.data["callConnectionId"]
            app.logger.info("CORRELATION ID: - %s", event.data["correlationId"])
            app.logger.info("CALL CONNECTION ID:--> %s", event.data["callConnectionId"])
            
            properties = await get_call_properties()
            # app.logger.info("Media streaming subscripton id:--> %s",properties.media_streaming_subscription.id)
            # app.logger.info("Media streaming subscripton state:--> %s",properties.media_streaming_subscription.state)
            
            # app.logger.info("Transcription subscripton id:--> %s",properties.transcription_subscription.id)
            # app.logger.info("Transcription subscripton state:--> %s",properties.transcription_subscription.state)
                
        elif event.type == "Microsoft.Communication.ConnectFailed":
            app.logger.info(f"Received ConnectFailed event for connection id: {event.data["callConnectionId"]}")
            resultInformation = event.data['resultInformation']
            call_connection_id = event.data["callConnectionId"]
            app.logger.info("Encountered error during connect, message=%s, code=%s, subCode=%s", resultInformation['message'], resultInformation['code'], resultInformation['subCode'])          
        elif event.type == "Microsoft.Communication.AddParticipantSucceeded":
            app.logger.info(f"Received AddParticipantSucceeded event for connection id: {event.data["callConnectionId"]}")
            call_connection_id = event.data["callConnectionId"]
                
        elif event.type == "Microsoft.Communication.RecognizeCompleted":
            app.logger.info(f"Received RecognizeCompleted event for connection id: {event.data["callConnectionId"]}")
            call_connection_id = event.data["callConnectionId"]
            if event.data['recognitionType'] == "dtmf": 
                tones = event.data['dtmfResult']['tones'] 
                app.logger.info("Recognition completed, tones=%s, context=%s", tones, event.data['operationContext']) 
            elif event.data['recognitionType'] == "choices": 
                labelDetected = event.data['choiceResult']['label']; 
                phraseDetected = event.data['choiceResult']['recognizedPhrase']; 
                app.logger.info("Recognition completed, labelDetected=%s, phraseDetected=%s, context=%s", labelDetected, phraseDetected, event.data['operationContext']); 
            elif event.data['recognitionType'] == "speech": 
                text = event.data['speechResult']['speech']; 
                app.logger.info("Recognition completed, text=%s, context=%s", text, event.data['operationContext']); 
            else: 
                app.logger.info("Recognition completed: data=%s", event.data); 

        elif event.type == "Microsoft.Communication.RecognizeFailed":
            if "operationContext" in event.data:
                opContext = event.data['operationContext']
                app.logger.info("Operation context--> %s", opContext)
            call_connection_id = event.data["callConnectionId"]
            resultInformation = event.data['resultInformation']
            app.logger.info("Encountered error during Recognize, message=%s, code=%s, subCode=%s", resultInformation['message'], resultInformation['code'], resultInformation['subCode'])
            app.logger.info("Play failed source index--> %s", event.data["failedPlaySourceIndex"])     

        elif event.type in "Microsoft.Communication.PlayCompleted":
            app.logger.info(f"Received PlayCompleted event for connection id: {call_connection_id}")
            if "operationContext" in event.data:
                opContext = event.data['operationContext']
                app.logger.info("Operation context--> %s", opContext)
            call_connection_id = event.data["callConnectionId"]
            
        elif event.type in "Microsoft.Communication.PlayFailed":
            app.logger.info(f"Received PlayFailed event for connection id: {call_connection_id}")
            if "operationContext" in event.data:
                opContext = event.data['operationContext']
                app.logger.info("Operation context--> %s", opContext)
            call_connection_id = event.data["callConnectionId"]
            resultInformation = event.data['resultInformation']
            app.logger.info("Encountered error during play, message=%s, code=%s, subCode=%s", resultInformation['message'], resultInformation['code'], resultInformation['subCode'])
            app.logger.info("Play failed source index--> %s", event.data["failedPlaySourceIndex"])
              
        elif event.type == "Microsoft.Communication.ContinuousDtmfRecognitionToneReceived":
            app.logger.info(f"Received ContinuousDtmfRecognitionToneReceived event for connection id: {call_connection_id}")
            app.logger.info(f"Tone received:-->: {event.data['tone']}")
            app.logger.info(f"Sequence Id:--> {event.data['sequenceId']}")
            call_connection_id = event.data["callConnectionId"]
                
        elif event.type == "Microsoft.Communication.ContinuousDtmfRecognitionToneFailed":
            app.logger.info(f"Received ContinuousDtmfRecognitionToneFailed event for connection id: {call_connection_id}")
            if "operationContext" in event.data:
                opContext = event.data['operationContext']
                app.logger.info("Operation context--> %s", opContext)
            call_connection_id = event.data["callConnectionId"]
            resultInformation = event.data['resultInformation']
            app.logger.info("Encountered error:- message=%s, code=%s, subCode=%s", resultInformation['message'], resultInformation['code'],resultInformation['subCode'])      
                
        elif event.type == "Microsoft.Communication.ContinuousDtmfRecognitionStopped":
            call_connection_id = event.data["callConnectionId"]
            app.logger.info(f"Received ContinuousDtmfRecognitionStopped event for connection id: {call_connection_id}")
                
        elif event.type == "Microsoft.Communication.SendDtmfTonesCompleted":
            app.logger.info(f"Received SendDtmfTonesCompleted event for connection id: {call_connection_id}")
            call_connection_id = event.data["callConnectionId"]
                
        elif event.type == "Microsoft.Communication.SendDtmfTonesFailed":
            app.logger.info(f"Received SendDtmfTonesFailed event for connection id: {call_connection_id}")
            resultInformation = event.data['resultInformation']
            call_connection_id = event.data["callConnectionId"]
            app.logger.info("Encountered error:- message=%s, code=%s, subCode=%s", resultInformation['message'], resultInformation['code'],resultInformation['subCode'])      
                
        elif event.type == "Microsoft.Communication.RemoveParticipantSucceeded":
            call_connection_id = event.data["callConnectionId"]
            app.logger.info(f"Received RemoveParticipantSucceeded event for connection id: {call_connection_id}")
               
        elif event.type == "Microsoft.Communication.RemoveParticipantFailed":
            call_connection_id = event.data["callConnectionId"]
            app.logger.info(f"Received RemoveParticipantFailed event for connection id: {call_connection_id}")
            call_connection_id = event.data["callConnectionId"]
            app.logger.info("Encountered error:- message=%s, code=%s, subCode=%s", resultInformation['message'], resultInformation['code'],resultInformation['subCode'])      

        # elif event.type == "Microsoft.Communication.MediaStreamingStarted":
        #     app.logger.info("Media Streaming Started.")
        #     call_connection_id = event.data["callConnectionId"]
        #     mediaStreamingUpdate = event.data['mediaStreamingUpdate']
        #     # app.logger.info(event.data['operationContext'])
        #     app.logger.info("Media streaming content type:--> %s",mediaStreamingUpdate["contentType"])
        #     app.logger.info("Media streaming status:--> %s",mediaStreamingUpdate["mediaStreamingStatus"])
        #     app.logger.info("Media streaming status details:--> %s",mediaStreamingUpdate["mediaStreamingStatusDetails"])
            
        # elif event.type == "Microsoft.Communication.MediaStreamingStopped":
        #     app.logger.info("Media Streaming Stopped.")
        #     call_connection_id = event.data["callConnectionId"]
        #     mediaStreamingUpdate = event.data['mediaStreamingUpdate']
        #     app.logger.info("Media streaming content type:--> %s",mediaStreamingUpdate["contentType"])
        #     app.logger.info("Media streaming status:--> %s",mediaStreamingUpdate["mediaStreamingStatus"])
        #     app.logger.info("Media streaming status details:--> %s",mediaStreamingUpdate["mediaStreamingStatusDetails"])
            
        # elif event.type == "Microsoft.Communication.MediaStreamingFailed":
        #     app.logger.info("Media Streaming Failed.")
        #     call_connection_id = event.data["callConnectionId"]
        #     resultInformation = event.data['resultInformation']
        #     app.logger.info("Encountered error during MediaStreaming, message=%s, code=%s, subCode=%s", resultInformation['message'], resultInformation['code'],resultInformation['subCode'])
            
        # elif event.type == "Microsoft.Communication.TranscriptionStarted":
        #     app.logger.info("Transcription Started.")
        #     call_connection_id = event.data["callConnectionId"]
        #     transcriptionUpdate = event.data['transcriptionUpdate']
        #     # app.logger.info(event.data['operationContext'])
        #     app.logger.info("Transcription status--> %s",transcriptionUpdate["transcriptionStatus"])
        #     app.logger.info("Transcription status details--> %s", transcriptionUpdate["transcriptionStatusDetails"])
            
        # elif event.type == "Microsoft.Communication.TranscriptionStopped":
        #     app.logger.info("Transcription Stopped.")
        #     call_connection_id = event.data["callConnectionId"]
        #     transcriptionUpdate = event.data['transcriptionUpdate']
        #     # app.logger.info(event.data['operationContext'])
        #     app.logger.info("Transcription status--> %s",transcriptionUpdate["transcriptionStatus"])
        #     app.logger.info("Transcription status details--> %s", transcriptionUpdate["transcriptionStatusDetails"])
            
        # elif event.type == "Microsoft.Communication.TranscriptionUpdated":
        #     app.logger.info("Transcription Updated.")
        #     call_connection_id = event.data["callConnectionId"]
        #     transcriptionUpdate = event.data['transcriptionUpdate']
        #     # app.logger.info(event.data['operationContext'])
        #     app.logger.info("Transcription status--> %s",transcriptionUpdate["transcriptionStatus"])
        #     app.logger.info("Transcription status details--> %s", transcriptionUpdate["transcriptionStatusDetails"])
            
        # elif event.type == "Microsoft.Communication.TranscriptionFailed":
        #     app.logger.info("Transcription Failed.")
        #     resultInformation = event.data['resultInformation']
        #     call_connection_id = event.data["callConnectionId"]
        #     app.logger.info("Encountered error during Transcription, message=%s, code=%s, subCode=%s", resultInformation['message'], resultInformation['code'],resultInformation['subCode'])
            
        elif event.type == "Microsoft.Communication.HoldFailed":
            app.logger.info("Hold Failed.")
            call_connection_id = event.data["callConnectionId"]
            resultInformation = event.data['resultInformation']
            app.logger.info("Encountered error during Hold, message=%s, code=%s, subCode=%s", resultInformation['message'], resultInformation['code'],resultInformation['subCode'])
            
        elif event.type == "Microsoft.Communication.PlayStarted":
            app.logger.info("PlayStarted event received.")
            call_connection_id = event.data["callConnectionId"]
        
        elif event.type in "Microsoft.Communication.PlayCanceled":
            app.logger.info(f"Received PlayCanceled event for connection id: {call_connection_id}")
            if "operationContext" in event.data:
                opContext = event.data['operationContext']
                app.logger.info("Operation context--> %s", opContext)
            call_connection_id = event.data["callConnectionId"]
                
        elif event.type in "Microsoft.Communication.RecognizeCanceled":
            app.logger.info(f"Received RecognizeCanceled event for connection id: {call_connection_id}")
            if "operationContext" in event.data:
                opContext = event.data['operationContext']
                app.logger.info("Operation context--> %s", opContext)
            call_connection_id = event.data["callConnectionId"]

        elif event.type == "Microsoft.Communication.RecordingStateChanged":
            call_connection_id = event.data["callConnectionId"]          
            app.logger.info(f"Received RecordingStateChanged event for connection id: {call_connection_id}")
                
        elif event.type == "Microsoft.Communication.CallTransferAccepted":
            call_connection_id = event.data["callConnectionId"]          
            app.logger.info(f"Received CallTransferAccepted event for connection id: {call_connection_id}") 
                
        elif event.type == "Microsoft.Communication.CallTransferFailed":
            app.logger.info(f"Received CallTransferFailed event for connection id: {call_connection_id}")
            if "operationContext" in event.data:
                opContext = event.data['operationContext']
                app.logger.info("Operation context--> %s", opContext)
            call_connection_id = event.data["callConnectionId"]
            resultInformation = event.data['resultInformation']
            app.logger.info("Encountered error:- message=%s, code=%s, subCode=%s", resultInformation['message'], resultInformation['code'],resultInformation['subCode'])

        elif event.type == "Microsoft.Communication.AddParticipantSucceeded":
            call_connection_id = event.data["callConnectionId"]          
            app.logger.info(f"Received AddParticipantSucceeded event for connection id: {call_connection_id}")

        elif event.type == "Microsoft.Communication.AddParticipantFailed":
            app.logger.info(f"Received AddParticipantFailed event for connection id: {call_connection_id}")
            if "operationContext" in event.data:
                opContext = event.data['operationContext']
                app.logger.info("Operation context--> %s", opContext)
            call_connection_id = event.data["callConnectionId"]
            resultInformation = event.data['resultInformation']
            app.logger.info("Encountered error:- message=%s, code=%s, subCode=%s", resultInformation['message'], resultInformation['code'],resultInformation['subCode'])
                
        elif event.type == "Microsoft.Communication.CancelAddParticipantSucceeded":
            call_connection_id = event.data["callConnectionId"]          
            app.logger.info(f"Received AddParticipantSucceeded event for connection id: {call_connection_id}")

        elif event.type == "Microsoft.Communication.CancelAddParticipantFailed":
            app.logger.info(f"Received AddParticipantFailed event for connection id: {call_connection_id}")
            if "operationContext" in event.data:
                opContext = event.data['operationContext']
                app.logger.info("Operation context--> %s", opContext)
            call_connection_id = event.data["callConnectionId"]
            resultInformation = event.data['resultInformation']
            app.logger.info("Encountered error:- message=%s, code=%s, subCode=%s", resultInformation['message'], resultInformation['code'],resultInformation['subCode'])
            
        elif event.type == "Microsoft.Communication.CreateCallFailed":
            app.logger.info(f"Received CreateCallFailed event for connection id: {call_connection_id}")
            if "operationContext" in event.data:
                opContext = event.data['operationContext']
                app.logger.info("Operation context--> %s", opContext)
            call_connection_id = event.data["callConnectionId"]
            resultInformation = event.data['resultInformation']
            app.logger.info("Encountered error:- message=%s, code=%s, subCode=%s", resultInformation['message'], resultInformation['code'],resultInformation['subCode'])
                
        elif event.type == "Microsoft.Communication.CallDisconnected":          
            app.logger.info(f"Received CallDisconnected event for connection id: {call_connection_id}")       

    return Response(status=200)

@app.route('/download')
async def download_recording():
        try:
            app.logger.info("Content location : %s", content_location)
            recording_data = await call_automation_client.download_recording(content_location)
            with open("Recording_File.wav", "wb") as binary_file:
                binary_file.write(recording_data.read())
            return redirect("/")
        except Exception as ex:
            app.logger.info("Failed to download recording --> " + str(ex))
            return Response(text=str(ex), status=500)

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

@app.route('/downloadMetadata')
async def download_metadata():
        try:
            app.logger.info("Metadata location : %s", metadata_location)
            recording_data = await call_automation_client.download_recording(metadata_location)
            with open("Recording_metadata.json", "wb") as binary_file:
                binary_file.write(recording_data.read())
            return redirect("/")
        except Exception as ex:
            app.logger.info("Failed to download meatadata --> " + str(ex))
            return Response(text=str(ex), status=500)

# GET endpoint to place phone call
@app.route('/outboundCall')
async def outbound_call_handler():
    await create_call()
    return redirect("/")

@app.route('/groupCall')
async def group_call_handler():
    await create_group_call()
    return redirect("/")

@app.route('/connectCall')
async def connect_call_handler():
    await connect_call()
    return redirect("/")

@app.route('/playMedia')
async def play_media_handler():
    await play_media()
    return redirect("/")

@app.route('/recognizeMedia')
async def play_recogniz_handler():
    await play_recognize()
    return redirect("/")

@app.route('/startContinuousDtmf')
async def start_continuous_dtmf_tones_handler():
    await start_continuous_dtmf()
    return redirect("/")

@app.route('/stopContinuousDtmf')
async def stop_continuous_dtmf_tones_handler():
    await stop_continuous_dtmf()
    return redirect("/")

@app.route('/sendDtmfTones')
async def send_dtmf_tones_handler():
    await start_send_dtmf_tones()
    return redirect("/")

@app.route('/addParticipant')
async def add_participant_handler():
    await add_participant()
    return redirect("/")

@app.route('/removeParticipant')
async def remove_participant_handler():
    await remove_participant()
    return redirect("/")

@app.route('/muteParticipant')
async def mute_participant_handler():
    await mute_participant()
    return redirect("/")

@app.route('/holdParticipant')
async def hold_participant_handler():
    await hold_participant()
    return redirect("/")

@app.route('/unholdParticipant')
async def unhold_participant_handler():
    await unhold_participant()
    return redirect("/")

@app.route('/getParticipant')
async def get_participant_handler():
    target = get_communication_target()
    await get_participant(target)
    return redirect("/")

@app.route('/listParticipant')
async def get_participant_list_handler():
    await get_participant_list()
    return redirect("/")

@app.route('/transferCallToParticipant')
async def transfer_call_to_participant_handler():
    await transfer_call_to_participant()
    return redirect("/")

@app.route('/startRecording')
async def start_recording_handler():
    await start_recording()
    return redirect("/")

@app.route('/pauseRecording')
async def pause_recording_handler():
    await pause_recording()
    return redirect("/")

@app.route('/resumeRecording')
async def resume_recording_handler():
    await resume_recording()
    return redirect("/")

@app.route('/stopRecording')
async def stop_recording_handler():
    await stop_recording()
    return redirect("/")

# @app.route('/startMediaStreaming')
# def start_media_streaming_handler():
#     start_media_streaming()
#     return redirect("/")

# @app.route('/stopMediaStreaming')
# def stop_media_streaming_handler():
#     stop_media_streaming()
#     return redirect("/")

# @app.route('/startTranscription')
# def start_transcription_handler():
#     start_transcription()
#     return redirect("/")

# @app.route('/updateTranscription')
# def update_transcription_handler():
#     update_transcription()
#     return redirect("/")

# @app.route('/stopTranscription')
# def stop_transcription_handler():
#     stop_transcription()
#     return redirect("/")

@app.route('/playWithInterruptMediaFlag')
async def play_with_interrupt_media_flag_handler():
    await play_with_interrupt_media_flag()
    return redirect("/")

@app.route('/cancelAllMediaOperation')
async def cancel_all_media_oparation_handler():
    await cancel_all_media_oparation()
    return redirect("/")

@app.route('/hangupCall')
async def hangup_call_handler():
    await hangup_call()
    return redirect("/")

@app.route('/terminateCall')
async def terminate_call_handler():
    await terminate_call()
    return redirect("/")

# GET endpoint to render the menus
@app.route('/')
async def index_handler():
    return await render_template("index.html")


if __name__ == '__main__':
    app.logger.setLevel(INFO)
    app.run(port=8080)
