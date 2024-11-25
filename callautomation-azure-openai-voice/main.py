from azure.eventgrid import EventGridEvent, SystemEventNames
from flask import Flask, Response, request, json, send_file, render_template, redirect
from logging import INFO
from azure.communication.callautomation import (
    CallAutomationClient,
    CommunicationUserIdentifier,
    PhoneNumberIdentifier,
    RecognizeInputType,
    RecognitionChoice,
    DtmfTone,
    TextSource,
    FileSource,
    SsmlSource,
    CommunicationIdentifier,
    MediaStreamingOptions,
    MediaStreamingTransportType,
    MediaStreamingContentType,
    MediaStreamingAudioChannelType,
    AudioFormat
    )
from azure.core.messaging import CloudEvent
from pyexpat import model
import time
import uuid
from urllib.parse import urlencode, urljoin

# Your ACS resource connection string
ACS_CONNECTION_STRING = ""

# Your ACS resource phone number will act as source number to start outbound call
ACS_PHONE_NUMBER = "<ACS_PHONE_NUMBER>"

# Target phone number you want to receive the call.
TARGET_PHONE_NUMBER = "<TARGET_PHONE_NUMBER>"

PARTICIPANT_PHONE_NUMBER = ""

PARTICIPANT_COMMUNICATION_USER=""

# Callback events URI to handle callback events.
CALLBACK_URI_HOST = "https://m2shmfdv-8080.inc1.devtunnels.ms"
CALLBACK_EVENTS_URI = CALLBACK_URI_HOST + "/api/callbacks"
COGNITIVE_SERVICES_ENDPOINT = ""

#(OPTIONAL) Your target Microsoft Teams user Id ex. "ab01bc12-d457-4995-a27b-c405ecfe4870"
TARGET_TEAMS_USER_ID = "<TARGET_TEAMS_USER_ID>"

TEMPLATE_FILES_PATH = "template"

# Prompts for text to speech
SPEECH_TO_TEXT_VOICE = "en-US-NancyNeural"
MAIN_MENU = "Hello this is Contoso Bank, we’re calling in regard to your appointment tomorrow at 9am to open a new account. Please say confirm if this time is still suitable for you or say cancel if you would like to cancel this appointment."
CONFIRMED_TEXT = "Thank you for confirming your appointment tomorrow at 9am, we look forward to meeting with you."
CANCEL_TEXT = "Your appointment tomorrow at 9am has been cancelled. Please call the bank directly if you would like to rebook for another date and time."
CUSTOMER_QUERY_TIMEOUT = "I’m sorry I didn’t receive a response, please try again."
NO_RESPONSE = "I didn't receive an input, we will go ahead and confirm your appointment. Goodbye"
INVALID_AUDIO = "I’m sorry, I didn’t understand your response, please try again."
CONFIRM_CHOICE_LABEL = "Confirm"
CANCEL_CHOICE_LABEL = "Cancel"
RETRY_CONTEXT = "retry"

TEMPLATE_FILES_PATH = "template"
AUDIO_FILES_PATH = "/audio"
MAIN_MENU_PROMPT_URI = CALLBACK_URI_HOST + AUDIO_FILES_PATH + "/MainMenu.wav"

TRANSPORT_URL="wss://m2shmfdv-5001.inc1.devtunnels.ms/ws"
RECOGNITION_PROMPT = "Hello this is contoso recognition test please confirm or cancel to proceed further."
PLAY_PROMPT = "Welcome to the Contoso Utilities. Thank you!"
SSML_PLAY_TEXT = "<speak version=\"1.0\" xmlns=\"http://www.w3.org/2001/10/synthesis\" xml:lang=\"en-US\"><voice name=\"en-US-JennyNeural\">Welcome to the Contoso Utilities. Played through SSML. Thank you!</voice></speak>"
SSML_RECOGNITION_TEXT = "<speak version=\"1.0\" xmlns=\"http://www.w3.org/2001/10/synthesis\" xml:lang=\"en-US\"><voice name=\"en-US-JennyNeural\">Hello this is SSML recognition test please confirm or cancel to proceed further. Thank you!</voice></speak>"
HOLD_PROMPT = "You are on hold please wait."
SSML_HOLD_TEXT = "<speak version=\"1.0\" xmlns=\"http://www.w3.org/2001/10/synthesis\" xml:lang=\"en-US\"><voice name=\"en-US-JennyNeural\">You are on hold please wait. Played through SSML. Thank you!</voice></speak>"
INTERRUPT_PROMPT = "Play is interrupted."
SSML_INTERRUPT_TEXT = "<speak version=\"1.0\" xmlns=\"http://www.w3.org/2001/10/synthesis\" xml:lang=\"en-US\"><voice name=\"en-US-JennyNeural\">Play is interrupted. Played through SSML. Thank you!</voice></speak>"

call_automation_client = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)
# call_connection_id = ""
app = Flask(__name__,
            template_folder=TEMPLATE_FILES_PATH)

def get_choices():
    choices = [
                RecognitionChoice(label = CONFIRM_CHOICE_LABEL, phrases= ["Confirm", "First", "One"], tone = DtmfTone.ONE),
                RecognitionChoice(label = CANCEL_CHOICE_LABEL, phrases= ["Cancel", "Second", "Two"], tone = DtmfTone.TWO)
            ]
    return choices

def play_recognize():
     
    text_source = TextSource(text=RECOGNITION_PROMPT, voice_name="en-US-NancyNeural")
    file_source = FileSource(url=MAIN_MENU_PROMPT_URI)
    ssml_text = SsmlSource(ssml_text=SSML_RECOGNITION_TEXT)
    play_sources = [text_source,file_source,ssml_text]
    target = get_communication_target()
     
    call_automation_client.get_call_connection(call_connection_id).start_recognizing_media(
                input_type=RecognizeInputType.CHOICES,
                target_participant=target,
                choices=get_choices(),
                play_prompt=text_source,
                interrupt_prompt=False,
                initial_silence_timeout=10,
                operation_context="choiceContext")
     
    # call_automation_client.get_call_connection(call_connection_id).start_recognizing_media(
    #             input_type=RecognizeInputType.DTMF,
    #             target_participant=target,
    #             # play_prompt=text_source,
    #             play_prompt=text_source,
    #             dtmf_max_tones_to_collect=1,
    #             interrupt_prompt=False,
    #             initial_silence_timeout=10,
    #             operation_context="dtmfContext"
    #         )
     
    # call_automation_client.get_call_connection(call_connection_id).start_recognizing_media( 
    #             input_type=RecognizeInputType.SPEECH, 
    #             target_participant=target, 
    #             end_silence_timeout=10, 
    #             play_prompt=text_source, 
    #             operation_context="OpenQuestionSpeech")
     
    # call_automation_client.get_call_connection(call_connection_id).start_recognizing_media( 
    #             dtmf_max_tones_to_collect=1, 
    #             input_type=RecognizeInputType.SPEECH_OR_DTMF, 
    #             target_participant=target, 
    #             end_silence_timeout=10, 
    #             play_prompt=text_source, 
    #             initial_silence_timeout=30, 
    #             interrupt_prompt=True, 
    #             operation_context="OpenQuestionSpeechOrDtmf")
     
def play_media():
     is_play_to_all = False
     
     text_source = TextSource(text=PLAY_PROMPT, voice_name="en-US-NancyNeural")
     file_source = FileSource(url=MAIN_MENU_PROMPT_URI)
     ssml_text = SsmlSource(ssml_text=SSML_PLAY_TEXT)
     
     target = get_communication_target()

     play_sources = [text_source,file_source,ssml_text]
     
     if(is_play_to_all):
          call_automation_client.get_call_connection(call_connection_id).play_media_to_all(
               play_source=play_sources,
               operation_context="playToAllContext"
               )
     else:
          call_automation_client.get_call_connection(call_connection_id).play_media(
               play_source=play_sources,
               play_to=[target],
               operation_context="playToContext")
    

def start_continuous_dtmf():
    target = get_communication_target()
    call_automation_client.get_call_connection(call_connection_id).start_continuous_dtmf_recognition(target_participant=target)
    app.logger.info("Continuous Dtmf recognition started. press 1 on dialpad.")

def stop_continuous_dtmf():
    target = get_communication_target()
    call_automation_client.get_call_connection(call_connection_id).stop_continuous_dtmf_recognition(target_participant=target)
    app.logger.info("Continuous Dtmf recognition stopped.")

def start_send_dtmf_tones():
    target = get_communication_target()
    tones = [DtmfTone.ONE,DtmfTone.TWO]
    call_automation_client.get_call_connection(call_connection_id).send_dtmf_tones(tones=tones,target_participant=target)
    app.logger.info("Send dtmf tone started.")

def start_media_streaming():
     call_automation_client.get_call_connection(call_connection_id).start_media_streaming(
        operation_callback_url=CALLBACK_EVENTS_URI,
        operation_context="startMediaStreamingContext")

def stop_media_streaming():
    call_automation_client.get_call_connection(call_connection_id).stop_media_streaming(
    operation_callback_url=CALLBACK_EVENTS_URI,
    operation_context="stopMediaStreamingContext")
     
def start_transcription():
    call_automation_client.get_call_connection(call_connection_id).start_transcription(
    locale="en-us",
    operation_context="startTranscriptionContext")
    
def update_transcription():
    call_automation_client.get_call_connection(call_connection_id).update_transcription(
    locale="en-au",
    operation_context="updateTranscriptionContext")
    
def stop_transcription():
    call_automation_client.get_call_connection(call_connection_id).stop_transcription(
    operation_context="stopTranscriptionContext")
    
def hold_participant():
    
    text_source = TextSource(text=HOLD_PROMPT, voice_name="en-US-NancyNeural")
    file_source = FileSource(url=MAIN_MENU_PROMPT_URI)
    ssml_text = SsmlSource(ssml_text=SSML_HOLD_TEXT)
     
    target = get_communication_target()
    call_automation_client.get_call_connection(call_connection_id).hold(
    target_participant=target,
    play_source=text_source,
    operation_context="holdUserContext")
    
    time.sleep(5)
    
    result = get_participant(target)
    app.logger.info("Participant:--> %s",result.identifier.raw_id)
    app.logger.info("Is participant on hold:--> %s",result.is_on_hold)
    
def unhold_participant():
    target = get_communication_target()
    call_automation_client.get_call_connection(call_connection_id).unhold(
    target_participant=target,
    operation_context="unholdUserContext")
     
    time.sleep(5)
    
    result = get_participant(target)
    app.logger.info("Participant:--> %s",result.identifier.raw_id)
    app.logger.info("Is participant on hold:--> %s",result.is_on_hold)

    
def play_with_interrupt_media_flag():
    text_source = TextSource(text=INTERRUPT_PROMPT, voice_name="en-US-NancyNeural")
    file_source = FileSource(url=MAIN_MENU_PROMPT_URI)
    ssml_text = SsmlSource(ssml_text=SSML_INTERRUPT_TEXT)
    
    play_sources = [text_source,file_source,ssml_text]
    
    call_automation_client.get_call_connection(call_connection_id).play_media_to_all(
    play_source=play_sources,
    loop=True,
    operation_context="interruptMediaContext",
    operation_callback_url=CALLBACK_EVENTS_URI,
    interrupt_call_media_operation=True)
    
def mute_participant():
    target = get_communication_target()
    call_automation_client.get_call_connection(call_connection_id).mute_participant(
    target_participant=target,
    operation_context="muteParticipantContext")
    
    time.sleep(5)
    
    result = get_participant(target)
    app.logger.info("Participant:--> %s",result.identifier.raw_id)
    app.logger.info("Is participant muted:--> %s",result.is_muted)
    
def get_participant(target:CommunicationIdentifier):
    participant =  call_automation_client.get_call_connection(call_connection_id).get_participant(target)
    return participant
    
def get_participant_list():
    participants = call_automation_client.get_call_connection(call_connection_id).list_participants()
    app.logger.info("Listing participants in call")
    for page in participants.by_page():
        for participant in page:
            app.logger.info("-------------------------------------------------------------")
            app.logger.info("Participant: %s", participant.identifier.raw_id)
            app.logger.info("Is participant muted: %s", participant.is_muted)
            app.logger.info("Is participant on hold: %s", participant.is_on_hold)
            app.logger.info("-------------------------------------------------------------")

def hangup_call():
    call_automation_client.get_call_connection(call_connection_id).hang_up(False)
    
def terminate_call():
    call_automation_client.get_call_connection(call_connection_id).hang_up(True)

def get_communication_target():
    is_acs_user = False
    target = CommunicationUserIdentifier(PARTICIPANT_COMMUNICATION_USER) if is_acs_user else PhoneNumberIdentifier(PARTICIPANT_PHONE_NUMBER)
    return target

def get_call_properties():
     call_properties = call_automation_client.get_call_connection(call_connection_id).get_call_properties()
     return call_properties

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
                media_streaming_options = MediaStreamingOptions(
                        transport_url=TRANSPORT_URL,
                        transport_type=MediaStreamingTransportType.WEBSOCKET,
                        content_type=MediaStreamingContentType.AUDIO,
                        audio_channel_type=MediaStreamingAudioChannelType.MIXED,
                        start_media_streaming=True,
                        enable_bidirectional=True,
                        audio_format=AudioFormat.PCM24_K_MONO)
                
                answer_call_result = call_automation_client.answer_call(incoming_call_context=incoming_call_context,
                                                                        cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT,
                                                                        callback_url=callback_uri, media_streaming=media_streaming_options)
                app.logger.info("Answered call for connection id: %s",
                                answer_call_result.call_connection_id)
            return Response(status=200)

# POST endpoint to handle callback events
@app.route("/api/callbacks/<contextId>", methods=["POST"])
def callback_events_handler(contextId):
    for event_dict in request.json:
        # Parsing callback events
        global call_connection_id
        event = CloudEvent.from_dict(event_dict)
        call_connection_id = event.data['callConnectionId']
        app.logger.info("%s event received for call connection id: %s", event.type, call_connection_id)
        call_connection_client = call_automation_client.get_call_connection(call_connection_id)
        target_participant = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
        if event.type == "Microsoft.Communication.CallConnected":
                # call_connection_id = event.data["callConnectionId"]
                app.logger.info(f"Received CallConnected event for connection id: {call_connection_id}")
                app.logger.info("CORRELATION ID:--> %s", event.data["correlationId"])
                app.logger.info("CALL CONNECTION ID:--> %s", event.data["callConnectionId"])
                
                # properties = get_call_properties()
                # app.logger.info("Media streaming subscripton id:--> %s",properties.media_streaming_subscription.id)
                # app.logger.info("Media streaming subscripton state:--> %s",properties.media_streaming_subscription.state)
                
                # app.logger.info("Transcription subscripton id:--> %s",properties.transcription_subscription.id)
                # app.logger.info("Transcription subscripton state:--> %s",properties.transcription_subscription.state)           
        elif event.type == "Microsoft.Communication.RecognizeCompleted":
                call_connection_id = event.data["callConnectionId"]
                app.logger.info(f"Received RecognizeCompleted event for connection id: {call_connection_id}")
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
                opContext = event.data['operationContext'] if event.data['operationContext'] else "EMPTY"
                app.logger.info("Operation context--> %s", opContext)
                call_connection_id = event.data["callConnectionId"]
                resultInformation = event.data['resultInformation']
                app.logger.info("Encountered error during Recognize, message=%s, code=%s, subCode=%s", resultInformation['message'], resultInformation['code'], resultInformation['subCode'])
                app.logger.info("Play failed source index--> %s", event.data["failedPlaySourceIndex"])
                
        elif event.type in "Microsoft.Communication.PlayCompleted":
                app.logger.info(f"Received PlayCompleted event for connection id: {call_connection_id}")
                opContext = event.data['operationContext'] if event.data['operationContext'] else "EMPTY"
                app.logger.info("Operation context--> %s", opContext) 
                call_connection_id = event.data["callConnectionId"]
                
        elif event.type in "Microsoft.Communication.PlayFailed":
                app.logger.info(f"Received PlayFailed event for connection id: {call_connection_id}")
                opContext = event.data['operationContext'] if event.data['operationContext'] else "EMPTY"
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
                opContext = event.data['operationContext'] if event.data['operationContext'] else "EMPTY"
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

        elif event.type == "Microsoft.Communication.MediaStreamingStarted":
                app.logger.info("Media Streaming Started.")
                call_connection_id = event.data["callConnectionId"]
                mediaStreamingUpdate = event.data['mediaStreamingUpdate']
                # app.logger.info(event.data['operationContext'])
                app.logger.info("Media streaming content type:--> %s",mediaStreamingUpdate["contentType"])
                app.logger.info("Media streaming status:--> %s",mediaStreamingUpdate["mediaStreamingStatus"])
                app.logger.info("Media streaming status details:--> %s",mediaStreamingUpdate["mediaStreamingStatusDetails"])
                
        elif event.type == "Microsoft.Communication.MediaStreamingStopped":
                app.logger.info("Media Streaming Stopped.")
                call_connection_id = event.data["callConnectionId"]
                mediaStreamingUpdate = event.data['mediaStreamingUpdate']
                app.logger.info("Media streaming content type:--> %s",mediaStreamingUpdate["contentType"])
                app.logger.info("Media streaming status:--> %s",mediaStreamingUpdate["mediaStreamingStatus"])
                app.logger.info("Media streaming status details:--> %s",mediaStreamingUpdate["mediaStreamingStatusDetails"])
                
        elif event.type == "Microsoft.Communication.MediaStreamingFailed":
                app.logger.info("Media Streaming Failed.")
                call_connection_id = event.data["callConnectionId"]
                resultInformation = event.data['resultInformation']
                app.logger.info("Encountered error during MediaStreaming, message=%s, code=%s, subCode=%s", 
                                    resultInformation['message'], 
                                    resultInformation['code'],
                                    resultInformation['subCode'])
                
        elif event.type == "Microsoft.Communication.TranscriptionStarted":
                app.logger.info("Transcription Started.")
                call_connection_id = event.data["callConnectionId"]
                transcriptionUpdate = event.data['transcriptionUpdate']
                # app.logger.info(event.data['operationContext'])
                app.logger.info("Transcription status--> %s",transcriptionUpdate["transcriptionStatus"])
                app.logger.info("Transcription status details--> %s", transcriptionUpdate["transcriptionStatusDetails"])
                
        elif event.type == "Microsoft.Communication.TranscriptionStopped":
                app.logger.info("Transcription Stopped.")
                call_connection_id = event.data["callConnectionId"]
                transcriptionUpdate = event.data['transcriptionUpdate']
                # app.logger.info(event.data['operationContext'])
                app.logger.info("Transcription status--> %s",transcriptionUpdate["transcriptionStatus"])
                app.logger.info("Transcription status details--> %s", transcriptionUpdate["transcriptionStatusDetails"])
                
        elif event.type == "Microsoft.Communication.TranscriptionUpdated":
                app.logger.info("Transcription Updated.")
                call_connection_id = event.data["callConnectionId"]
                transcriptionUpdate = event.data['transcriptionUpdate']
                # app.logger.info(event.data['operationContext'])
                app.logger.info("Transcription status--> %s",transcriptionUpdate["transcriptionStatus"])
                app.logger.info("Transcription status details--> %s", transcriptionUpdate["transcriptionStatusDetails"])
                
        elif event.type == "Microsoft.Communication.TranscriptionFailed":
                app.logger.info("Transcription Failed.")
                resultInformation = event.data['resultInformation']
                call_connection_id = event.data["callConnectionId"]
                app.logger.info("Encountered error during Transcription, message=%s, code=%s, subCode=%s", 
                                    resultInformation['message'], 
                                    resultInformation['code'],
                                    resultInformation['subCode'])
                
        elif event.type == "Microsoft.Communication.HoldFailed":
                app.logger.info("Hold Failed.")
                call_connection_id = event.data["callConnectionId"]
                resultInformation = event.data['resultInformation']
                app.logger.info("Encountered error during Hold, message=%s, code=%s, subCode=%s", 
                                    resultInformation['message'], 
                                    resultInformation['code'],
                                    resultInformation['subCode'])
                
        elif event.type == "Microsoft.Communication.PlayStarted":
                app.logger.info("PlayStarted event received.")
                call_connection_id = event.data["callConnectionId"]
            
        elif event.type in "Microsoft.Communication.PlayCanceled":
                app.logger.info(f"Received PlayCanceled event for connection id: {call_connection_id}")
                opContext = event.data['operationContext'] if event.data['operationContext'] else "EMPTY"
                app.logger.info("Operation context--> %s", opContext)
                call_connection_id = event.data["callConnectionId"]
                
        elif event.type in "Microsoft.Communication.RecognizeCanceled":
                app.logger.info(f"Received RecognizeCanceled event for connection id: {call_connection_id}")
                opContext = event.data['operationContext'] if event.data['operationContext'] else "EMPTY"
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
                opContext = event.data['operationContext'] if event.data['operationContext'] else "EMPTY"
                app.logger.info("Operation context--> %s", opContext) 
                call_connection_id = event.data["callConnectionId"]
                resultInformation = event.data['resultInformation']
                app.logger.info("Encountered error:- message=%s, code=%s, subCode=%s", resultInformation['message'], resultInformation['code'],resultInformation['subCode'])

        elif event.type == "Microsoft.Communication.AddParticipantSucceeded":
                call_connection_id = event.data["callConnectionId"]          
                app.logger.info(f"Received AddParticipantSucceeded event for connection id: {call_connection_id}")

        elif event.type == "Microsoft.Communication.AddParticipantFailed":
                app.logger.info(f"Received AddParticipantFailed event for connection id: {call_connection_id}")
                opContext = event.data['operationContext'] if event.data['operationContext'] else "EMPTY"
                app.logger.info("Operation context--> %s", opContext) 
                call_connection_id = event.data["callConnectionId"]
                resultInformation = event.data['resultInformation']
                app.logger.info("Encountered error:- message=%s, code=%s, subCode=%s", resultInformation['message'], resultInformation['code'],resultInformation['subCode'])
                
        elif event.type == "Microsoft.Communication.CancelAddParticipantSucceeded":
                call_connection_id = event.data["callConnectionId"]          
                app.logger.info(f"Received AddParticipantSucceeded event for connection id: {call_connection_id}")

        elif event.type == "Microsoft.Communication.CancelAddParticipantFailed":
                app.logger.info(f"Received AddParticipantFailed event for connection id: {call_connection_id}")
                opContext = event.data['operationContext'] if event.data['operationContext'] else "EMPTY"
                app.logger.info("Operation context--> %s", opContext) 
                call_connection_id = event.data["callConnectionId"]
                resultInformation = event.data['resultInformation']
                app.logger.info("Encountered error:- message=%s, code=%s, subCode=%s", resultInformation['message'], resultInformation['code'],resultInformation['subCode'])
                
        elif event.type == "Microsoft.Communication.CallDisconnected":          
                app.logger.info(f"Received CallDisconnected event for connection id: {call_connection_id}")

        return Response(status=200)

@app.route('/playMedia')
def play_media_handler():
    play_media()
    return redirect("/")

@app.route('/recognizeMedia')
def play_recogniz_handler():
    play_recognize()
    return redirect("/")

@app.route('/startContinuousDtmf')
def start_continuous_dtmf_tones_handler():
    start_continuous_dtmf()
    return redirect("/")

@app.route('/stopContinuousDtmf')
def stop_continuous_dtmf_tones_handler():
    stop_continuous_dtmf()
    return redirect("/")

@app.route('/sendDtmfTones')
def send_dtmf_tones_handler():
    start_send_dtmf_tones()
    return redirect("/")

@app.route('/muteParticipant')
def mute_participant_handler():
    mute_participant()
    return redirect("/")

@app.route('/holdParticipant')
def hold_participant_handler():
    hold_participant()
    return redirect("/")

@app.route('/unholdParticipant')
def unhold_participant_handler():
    unhold_participant()
    return redirect("/")

@app.route('/listParticipant')
def get_participant_list_handler():
    get_participant_list()
    return redirect("/")

@app.route('/startMediaStreaming')
def start_media_streaming_handler():
    start_media_streaming()
    return redirect("/")

@app.route('/stopMediaStreaming')
def stop_media_streaming_handler():
    stop_media_streaming()
    return redirect("/")

@app.route('/startTranscription')
def start_transcription_handler():
    start_transcription()
    return redirect("/")

@app.route('/updateTranscription')
def update_transcription_handler():
    update_transcription()
    return redirect("/")

@app.route('/stopTranscription')
def stop_transcription_handler():
    stop_transcription()
    return redirect("/")

@app.route('/playWithInterruptMediaFlag')
def play_with_interrupt_media_flag_handler():
    play_with_interrupt_media_flag()
    return redirect("/")

@app.route('/hangupCall')
def hangup_call_handler():
    hangup_call()
    return redirect("/")

@app.route('/terminateCall')
def terminate_call_handler():
    terminate_call()
    return redirect("/")

# GET endpoint to render the menus
@app.route('/')
def index_handler():
    return render_template("index.html")


if __name__ == '__main__':
    app.logger.setLevel(INFO)
    app.run(port=8080)
