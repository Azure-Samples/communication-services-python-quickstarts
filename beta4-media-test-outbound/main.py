from azure.eventgrid import EventGridEvent, SystemEventNames
from flask import Flask, Response, request, json, send_file, render_template, redirect
from logging import INFO
from azure.communication.callautomation import (
    CallAutomationClient,
    CallConnectionClient,
    PhoneNumberIdentifier,
    RecognizeInputType,
    MicrosoftTeamsUserIdentifier,
    CallInvite,
    RecognitionChoice,
    DtmfTone,
    TextSource,
    MediaStreamingOptions,
    MediaStreamingTransportType,
    MediaStreamingContentType,
    MediaStreamingAudioChannelType,
    FileSource,
    TranscriptionOptions,
    TranscriptionTransportType)
from azure.core.messaging import CloudEvent
import time
# Your ACS resource connection string
ACS_CONNECTION_STRING = ""

# Your ACS resource phone number will act as source number to start outbound call
ACS_PHONE_NUMBER = ""

# Target phone number you want to receive the call.
TARGET_PHONE_NUMBER = ""

# Callback events URI to handle callback events.
CALLBACK_URI_HOST = ""
CALLBACK_EVENTS_URI = CALLBACK_URI_HOST + "/api/callbacks"
COGNITIVE_SERVICES_ENDPOINT = ""

#(OPTIONAL) Your target Microsoft Teams user Id ex. "ab01bc12-d457-4995-a27b-c405ecfe4870"
TARGET_TEAMS_USER_ID = "<TARGET_TEAMS_USER_ID>"

TEMPLATE_FILES_PATH = "template"
AUDIO_FILES_PATH = "/audio"
MAIN_MENU_PROMPT_URI = CALLBACK_URI_HOST + AUDIO_FILES_PATH + "/MainMenu.wav"

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

call_automation_client = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)

app = Flask(__name__,
            static_folder=AUDIO_FILES_PATH.strip("/"),
            static_url_path=AUDIO_FILES_PATH,
            template_folder=TEMPLATE_FILES_PATH)

def get_choices():
    choices = [
                RecognitionChoice(label = CONFIRM_CHOICE_LABEL, phrases= ["Confirm", "First", "One"], tone = DtmfTone.ONE),
                RecognitionChoice(label = CANCEL_CHOICE_LABEL, phrases= ["Cancel", "Second", "Two"], tone = DtmfTone.TWO)
            ]
    return choices

def get_media_recognize_choice_options(call_connection_client: CallConnectionClient, text_to_play: str, target_participant:str, choices: any, context: str):
     play_source =  TextSource (text= text_to_play, voice_name= SPEECH_TO_TEXT_VOICE)
     call_connection_client.start_recognizing_media(
                input_type=RecognizeInputType.CHOICES,
                target_participant=target_participant,
                choices=choices,
                play_prompt=play_source,
                interrupt_prompt=False,
                initial_silence_timeout=10,
                operation_context=context
            )
     
def handle_play(call_connection_client: CallConnectionClient, text_to_play: str,context:str):
        play_source = TextSource(text=text_to_play, voice_name=SPEECH_TO_TEXT_VOICE) 
        call_connection_client.play_media_to_all(play_source,operation_context=context)

# GET endpoint to place phone call
@app.route('/outboundCall')
def outbound_call_handler():
    target_participant = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
    source_caller = PhoneNumberIdentifier(ACS_PHONE_NUMBER)
    
    # media_streaming_options = MediaStreamingOptions(
    #     transport_url="wss://e063-2409-40c2-4004-eced-9487-4dfb-b0e4-10fb.ngrok-free.app",
    #     transport_type=MediaStreamingTransportType.WEBSOCKET,
    #     content_type=MediaStreamingContentType.AUDIO,
    #     audio_channel_type=MediaStreamingAudioChannelType.UNMIXED,
    #     start_media_streaming=False
    #     )
    
    # transcription_options = TranscriptionOptions(
    #     transport_url="wss://e063-2409-40c2-4004-eced-9487-4dfb-b0e4-10fb.ngrok-free.app",
    #     transport_type=TranscriptionTransportType.WEBSOCKET,
    #     locale="en-US",
    #     start_transcription=False
    #     )
    call_connection_properties = call_automation_client.create_call(target_participant, 
                                                                    CALLBACK_EVENTS_URI,
                                                                    cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT,
                                                                    source_caller_id_number=source_caller,
                                                                    # media_streaming=media_streaming_options
                                                                    # transcription=transcription_options
                                                                    )
    app.logger.info("Created call with connection id: %s", call_connection_properties.call_connection_id)
    return redirect("/")


# POST endpoint to handle callback events
@app.route('/api/callbacks', methods=['POST'])
def callback_events_handler():
    for event_dict in request.json:
        # Parsing callback events
        event = CloudEvent.from_dict(event_dict)
        call_connection_id = event.data['callConnectionId']
        app.logger.info("%s event received for call connection id: %s", event.type, call_connection_id)
        call_connection_client = call_automation_client.get_call_connection(call_connection_id)
        target_participant = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
        if event.type == "Microsoft.Communication.CallConnected":
            # (Optional) Add a Microsoft Teams user to the call.  Uncomment the below snippet to enable Teams Interop scenario.
            # call_connection_client.add_participant(target_participant = CallInvite(
            #     target = MicrosoftTeamsUserIdentifier(user_id=TARGET_TEAMS_USER_ID),
            #     source_display_name = "Jack (Contoso Tech Support)"))
            app.logger.info("Call Connected.=%s", event.data)
            
            #call_connection_client.start_media_streaming()
            # call_connection_client.start_media_streaming(operation_callback_url=CALLBACK_EVENTS_URI, operation_context="startMediaStreamingContext")
            
            # call_connection_client.start_transcription()
            # call_connection_client.start_transcription(locale="en-AU",operation_context="startTranscrptionContext")
            # call_connection_client.start_transcription(operation_context="startTranscrptionContext")
            # time.sleep(5)
            # call_connection_client.update_transcription(locale="en-fjlsjf")
            app.logger.info("Starting recognize")
            get_media_recognize_choice_options(
                call_connection_client=call_connection_client,
                text_to_play=MAIN_MENU, 
                target_participant=target_participant,
                choices=get_choices(),context="")
        elif event.type == "Microsoft.Communication.MediaStreamingStarted":
            app.logger.info("Media Streaming Started.")
            app.logger.info("MediaStreamingStarted: data=%s", event.data) 
            mediaStreamingUpdate = event.data['mediaStreamingUpdate']
            # app.logger.info(event.data['operationContext'])
            app.logger.info(mediaStreamingUpdate["contentType"])
            app.logger.info(mediaStreamingUpdate["mediaStreamingStatus"])
            app.logger.info(mediaStreamingUpdate["mediaStreamingStatusDetails"])
            
        elif event.type == "Microsoft.Communication.MediaStreamingStopped":
            app.logger.info("Media Streaming Stopped.")
            app.logger.info("MediaStreamingStoppeddata=%s", event.data)
            mediaStreamingUpdate = event.data['mediaStreamingUpdate']
            app.logger.info(mediaStreamingUpdate["contentType"])
            app.logger.info(mediaStreamingUpdate["mediaStreamingStatus"])
            app.logger.info(mediaStreamingUpdate["mediaStreamingStatusDetails"])
            
        elif event.type == "Microsoft.Communication.MediaStreamingFailed":
            app.logger.info("Media Streaming Failed.")
            resultInformation = event.data['resultInformation']
            app.logger.info("Encountered error during MediaStreaming, message=%s, code=%s, subCode=%s", 
                                resultInformation['message'], 
                                resultInformation['code'],
                                resultInformation['subCode'])
        elif event.type == "Microsoft.Communication.TranscriptionStarted":
            app.logger.info("Transcription Started.")
            app.logger.info("TranscriptionStarted: data=%s", event.data) 
            transcriptionUpdate = event.data['transcriptionUpdate']
            # app.logger.info(event.data['operationContext'])
            app.logger.info(transcriptionUpdate["transcriptionStatus"])
            app.logger.info(transcriptionUpdate["transcriptionStatusDetails"])
        elif event.type == "Microsoft.Communication.TranscriptionStopped":
            app.logger.info("Transcription Stopped.")
            app.logger.info("TranscriptionStopped: data=%s", event.data) 
            transcriptionUpdate = event.data['transcriptionUpdate']
            # app.logger.info(event.data['operationContext'])
            app.logger.info(transcriptionUpdate["transcriptionStatus"])
            app.logger.info(transcriptionUpdate["transcriptionStatusDetails"])
        elif event.type == "Microsoft.Communication.TranscriptionUpdated":
            app.logger.info("Transcription Updated.")
            app.logger.info("TranscriptionUpdated: data=%s", event.data) 
            transcriptionUpdate = event.data['transcriptionUpdate']
            # app.logger.info(event.data['operationContext'])
            app.logger.info(transcriptionUpdate["transcriptionStatus"])
            app.logger.info(transcriptionUpdate["transcriptionStatusDetails"])
        elif event.type == "Microsoft.Communication.TranscriptionFailed":
            app.logger.info("Transcription Failed.")
            resultInformation = event.data['resultInformation']
            app.logger.info("Encountered error during Transcription, message=%s, code=%s, subCode=%s", 
                                resultInformation['message'], 
                                resultInformation['code'],
                                resultInformation['subCode'])
        elif event.type == "Microsoft.Communication.HoldFailed":
            app.logger.info("Hold Failed.")
            resultInformation = event.data['resultInformation']
            app.logger.info("Encountered error during Hold, message=%s, code=%s, subCode=%s", 
                                resultInformation['message'], 
                                resultInformation['code'],
                                resultInformation['subCode'])
        elif event.type == "Microsoft.Communication.PlayStarted":
            app.logger.info("PlayStarted event received.")
            app.logger.info("*******************************")
        # Perform different actions based on DTMF tone received from RecognizeCompleted event
        elif event.type == "Microsoft.Communication.RecognizeCompleted":
            app.logger.info("Recognize completed: data=%s", event.data) 
            if event.data['recognitionType'] == "choices": 
                 label_detected = event.data['choiceResult']['label']; 
                 phraseDetected = event.data['choiceResult']['recognizedPhrase']; 
                 app.logger.info("Recognition completed, labelDetected=%s, phraseDetected=%s, context=%s", label_detected, phraseDetected, event.data.get('operationContext'))
                 
                 #call_connection_client.stop_media_streaming()
                #  call_connection_client.stop_media_streaming(operation_callback_url=CALLBACK_EVENTS_URI)
                
                #  call_connection_client.stop_transcription()
                #  call_connection_client.stop_transcription(operation_context="stopTranscriptionContext")
                 
                 if label_detected == CONFIRM_CHOICE_LABEL:
                    text_to_play = CONFIRMED_TEXT
                 else:
                    text_to_play = CANCEL_TEXT
                #  time.sleep(5)
                 #call_connection_client.start_media_streaming()
                #  call_connection_client.start_media_streaming(operation_callback_url=CALLBACK_EVENTS_URI, operation_context="startMediaStreamingContext")
                
                #  call_connection_client.start_transcription()
                #  call_connection_client.start_transcription(locale="en-US",operation_context="startTranscrptionContext")
                #  time.sleep(5)
                #  call_connection_client.update_transcription(locale="en-AU")
                
                #  call_connection_client.hold(target_participant=PhoneNumberIdentifier(TARGET_PHONE_NUMBER))
                #  play_source = TextSource(text="You are on hold, Please wait.", voice_name=SPEECH_TO_TEXT_VOICE)
                #  play_source = FileSource(MAIN_MENU_PROMPT_URI)
                #  call_connection_client.hold(
                #      target_participant=PhoneNumberIdentifier(TARGET_PHONE_NUMBER),
                #      play_source=play_source,
                #      operation_context="holdUserContext",
                #      operation_callback_url=CALLBACK_EVENTS_URI
                #      )
                #  app.logger.info("Participant on hold..")
                #  app.logger.info("Waiting...")
                #  time.sleep(10)
                #  call_connection_client.unhold(target_participant=PhoneNumberIdentifier(TARGET_PHONE_NUMBER))
                #  call_connection_client.unhold(
                #      target_participant=PhoneNumberIdentifier(TARGET_PHONE_NUMBER),
                #      operation_context="holdUserContext")
                #  app.logger.info("Participant on unhold..")
                
                #  handle_play(call_connection_client=call_connection_client, text_to_play=text_to_play,context="textSourceContext")
                #  play_source = TextSource(text="This is interrupt call media test.", voice_name=SPEECH_TO_TEXT_VOICE)
                 play_source = FileSource(MAIN_MENU_PROMPT_URI)
                #  call_connection_client.play_media_to_all(
                #      play_source,
                #      interrupt_call_media_operation=False,
                #      operation_context="interruptContext",
                #      operation_callback_url=CALLBACK_EVENTS_URI,
                #      loop=False)
                
                 play_to = [PhoneNumberIdentifier(TARGET_PHONE_NUMBER)]
                 call_connection_client._play_media(
                     play_source,
                     play_to=play_to)
                
        elif event.type == "Microsoft.Communication.RecognizeFailed":
            failedContext = event.data['operationContext']
            if(failedContext and failedContext == RETRY_CONTEXT):
                handle_play(call_connection_client=call_connection_client, text_to_play=NO_RESPONSE)
            else:
                resultInformation = event.data['resultInformation']
                app.logger.info("Encountered error during recognize, message=%s, code=%s, subCode=%s", 
                                resultInformation['message'], 
                                resultInformation['code'],
                                resultInformation['subCode'])
                if(resultInformation['subCode'] in[8510, 8510]):
                    textToPlay =CUSTOMER_QUERY_TIMEOUT
                else :
                    textToPlay =INVALID_AUDIO
                
                get_media_recognize_choice_options(
                    call_connection_client=call_connection_client,
                    text_to_play=textToPlay, 
                    target_participant=target_participant,
                    choices=get_choices(),context=RETRY_CONTEXT)

        elif event.type in ["Microsoft.Communication.PlayCompleted"]:
            #app.logger.info("Terminating call")
            # app.logger.info(event.data['operationContext'])
           
            # call_connection_client.stop_media_streaming()
            # call_connection_client.stop_media_streaming(operation_callback_url=CALLBACK_EVENTS_URI)
            
            # call_connection_client.stop_transcription()
            # call_connection_client.stop_transcription(operation_context="stopTranscriptionContext")
            
            # if(event.data['operationContext'] == "textSourceContext"):
            #     # call_connection_client.start_media_streaming()
            #     # call_connection_client.start_media_streaming(operation_callback_url=CALLBACK_EVENTS_URI, operation_context="startMediaStreamingContext")
                
            #     # call_connection_client.start_transcription()
            #     call_connection_client.start_transcription(locale="en-AU",operation_context="startTranscrptionContext")
            #     time.sleep(5)
            #     call_connection_client.update_transcription(locale="en-AU")
            #     call_connection_client.play_media_to_all([FileSource(MAIN_MENU_PROMPT_URI)],operation_context="fileSourceContext")
            # elif (event.data['operationContext'] == "fileSourceContext"):
            #     # call_connection_client.start_media_streaming()
            #     # call_connection_client.start_media_streaming(operation_callback_url=CALLBACK_EVENTS_URI, operation_context="startMediaStreamingContext")
                
            #     # call_connection_client.start_transcription()
            #     call_connection_client.start_transcription(locale="en-US",operation_context="startTranscrptionContext")
            #     time.sleep(5)
            #     call_connection_client.update_transcription(locale="en-AU")
            #     handle_play(call_connection_client=call_connection_client, text_to_play="good bye",context="goodbyContext")
            # else:
            #     call_connection_client.hang_up(is_for_everyone=True)
            call_connection_client.hang_up(is_for_everyone=True)
        return Response(status=200)

# GET endpoint to render the menus
@app.route('/')
def index_handler():
    return render_template("index.html")


if __name__ == '__main__':
    app.logger.setLevel(INFO)
    app.run(port=5001)
