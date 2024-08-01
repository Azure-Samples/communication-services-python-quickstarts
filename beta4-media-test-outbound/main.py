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
    SsmlSource,
    TranscriptionOptions,
    TranscriptionTransportType)
from azure.core.messaging import CloudEvent
import time
# Your ACS resource connection string
ACS_CONNECTION_STRING = "endpoint=https://dacsrecordingtest.unitedstates.communication.azure.com/;accesskey=P03pgjuvw8Yo9nlRkdgjrm/TmT0yIkYt3fXowddBQ0QbOYZ6GbDaAir6om8N8sHOt7ifhJqT20aOsy4EDulO+A=="

# Your ACS resource phone number will act as source number to start outbound call
ACS_PHONE_NUMBER = "+18332638155"

# Target phone number you want to receive the call.
TARGET_PHONE_NUMBER = "+918688023395"

# Callback events URI to handle callback events.
CALLBACK_URI_HOST = "https://7hvxmj7n.inc1.devtunnels.ms:8080"
CALLBACK_EVENTS_URI = CALLBACK_URI_HOST + "/api/callbacks"
COGNITIVE_SERVICES_ENDPOINT = "https://cognitive-service-waferwire.cognitiveservices.azure.com/"

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
DTMF_TEXT = "Press 1, 2, 3, 4 on your key board!"

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

def get_media_recognize_options(call_connection_client: CallConnectionClient, text_to_play: str, target_participant:str, choices: any, context: str):
     play_source =  TextSource (text= text_to_play, voice_name= SPEECH_TO_TEXT_VOICE)
     file_source = FileSource("https://www2.cs.uic.edu/~i101/SoundFiles/StarWars3.wav")
     file_source_invalid = FileSource("https://dummy/dummy.wav")
     ssml_source = SsmlSource(ssml_text='<speak version=\"1.0\" xmlns=\"http://www.w3.org/2001/10/synthesis\" xml:lang=\"en-US\"><voice name=\"en-US-JennyNeural\">SSML Prompt</voice></speak>')
    #  play_prompts = [ssml_source, play_source, file_source, ssml_source, play_source, file_source,ssml_source, play_source, file_source,ssml_source]
     play_prompts = []
     call_connection_client.start_recognizing_media(
                input_type=RecognizeInputType.CHOICES,
                target_participant=target_participant,
                choices=choices,
                play_prompt=play_source,
                # play_prompt=play_prompts,
                interrupt_prompt=False,
                initial_silence_timeout=10,
                operation_context="choicesContext"
            )
    
    #  call_connection_client.start_recognizing_media(
    #             input_type=RecognizeInputType.DTMF,
    #             target_participant=target_participant,
    #             # play_prompt=play_source,
    #             play_prompt=play_prompts,
    #             dtmf_max_tones_to_collect=1,
    #             interrupt_prompt=False,
    #             initial_silence_timeout=10,
    #             operation_context="dtmfContext"
    #         )
     
    #  call_connection_client.start_recognizing_media( 
    #             input_type=RecognizeInputType.SPEECH, 
    #             target_participant=target_participant, 
    #             end_silence_timeout=10, 
    #             play_prompt=play_prompts, 
    #             operation_context="OpenQuestionSpeech")
     
    #  call_connection_client.start_recognizing_media( 
    #             dtmf_max_tones_to_collect=1, 
    #             input_type=RecognizeInputType.SPEECH_OR_DTMF, 
    #             target_participant=target_participant, 
    #             end_silence_timeout=10, 
    #             play_prompt=play_prompts, 
    #             initial_silence_timeout=30, 
    #             interrupt_prompt=True, 
    #             operation_context="OpenQuestionSpeechOrDtmf")
     
def handle_play(call_connection_client: CallConnectionClient, text_to_play: str,context:str):
        play_source = TextSource(text=text_to_play, voice_name=SPEECH_TO_TEXT_VOICE) 
        # play_source = FileSource("https://www2.cs.uic.edu/~i101/SoundFiles/StarWars3.wav")
        # play_source = TextSource(text="Hi, This is multiple play source call media test.", voice_name=SPEECH_TO_TEXT_VOICE)
        file_source = FileSource("https://www2.cs.uic.edu/~i101/SoundFiles/StarWars3.wav")
        file_source_invalid = FileSource("https://dummy/dummy.wav")
        ssml_source = SsmlSource(ssml_text='<speak version=\"1.0\" xmlns=\"http://www.w3.org/2001/10/synthesis\" xml:lang=\"en-US\"><voice name=\"en-US-JennyNeural\">SSML Prompt</voice></speak>')
        # play_sources = [ssml_source, play_source, file_source, ssml_source, play_source, file_source, ssml_source, play_source, file_source,ssml_source]
        play_sources = [file_source, file_source_invalid]
        call_connection_client.play_media_to_all(
                     play_source=play_sources,
                     interrupt_call_media_operation=False,
                     operation_context="playContext",
                     operation_callback_url=CALLBACK_EVENTS_URI,
                     loop=False
                     )
            
        # call_connection_client.play_media_to_all(play_source,operation_context=context)
        
        # Interrupt Play
        # play_source = TextSource(text="This is interrupt call media test.", voice_name=SPEECH_TO_TEXT_VOICE)
        # # play_source = FileSource("https://www2.cs.uic.edu/~i101/SoundFiles/StarWars3.wav")
        # call_connection_client.play_media_to_all(
        #                 play_source,
        #                 interrupt_call_media_operation=False,
        #                 operation_context="interruptContext",
        #                 operation_callback_url=CALLBACK_EVENTS_URI,
        #                 loop=False)
                
        # play_to = [PhoneNumberIdentifier(TARGET_PHONE_NUMBER)]
        # call_connection_client._play_media(
        #              play_source=play_sources,
        #              play_to=play_to
        #             #  interrupt_call_media_operation=False,
        #             #  operation_callback_url=CALLBACK_EVENTS_URI,
        #             #  loop=False,
        #             #  operation_context="playContext"
        #             )
# GET endpoint to place phone call
@app.route('/outboundCall')
def outbound_call_handler():
    target_participant = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
    source_caller = PhoneNumberIdentifier(ACS_PHONE_NUMBER)
    
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
        correlation_id = event.data['correlationId']
        app.logger.info("%s event received for call connection id: %s", event.type, call_connection_id)
        app.logger.info("%s CORRELATION ID ======>: %s", event.type, correlation_id)
        call_connection_client = call_automation_client.get_call_connection(call_connection_id)
        target_participant = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
        if event.type == "Microsoft.Communication.CallConnected":
            # (Optional) Add a Microsoft Teams user to the call.  Uncomment the below snippet to enable Teams Interop scenario.
            # call_connection_client.add_participant(target_participant = CallInvite(
            #     target = MicrosoftTeamsUserIdentifier(user_id=TARGET_TEAMS_USER_ID),
            #     source_display_name = "Jack (Contoso Tech Support)"))
            app.logger.info("Call Connected.=%s", event.data)
            app.logger.info("Starting recognize")
            get_media_recognize_options(
                call_connection_client=call_connection_client,
                text_to_play=MAIN_MENU, 
                target_participant=target_participant,
                choices=get_choices(),context="")
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
                 
                 call_connection_client.hold(target_participant=PhoneNumberIdentifier(TARGET_PHONE_NUMBER))
                 play_source = TextSource(text="You are on hold, Please wait.", voice_name=SPEECH_TO_TEXT_VOICE)
                #  play_source = FileSource("https://www2.cs.uic.edu/~i101/SoundFiles/StarWars3.wav")
                #  call_connection_client.hold(
                #      target_participant=PhoneNumberIdentifier(TARGET_PHONE_NUMBER),
                #     #  play_source=play_source,
                #      operation_context="holdUserContext",
                #      operation_callback_url=CALLBACK_EVENTS_URI
                #      )
                 app.logger.info("Participant on hold..")
                 app.logger.info("Waiting...")
                 time.sleep(10)
                 call_connection_client.unhold(target_participant=PhoneNumberIdentifier(TARGET_PHONE_NUMBER))
                #  call_connection_client.unhold(
                #      target_participant=PhoneNumberIdentifier(TARGET_PHONE_NUMBER),
                #      operation_context="holdUserContext")
                 app.logger.info("Participant on unhold..")
            elif event.data['recognitionType'] == "dtmf":
                tones = event.data['dtmfResult']['tones'] 
                app.logger.info("Recognition completed, tones=%s, context=%s", tones, event.data.get('operationContext'))
                # call_connection_client.hang_up(is_for_everyone=True)
            elif event.data['recognitionType'] == "speech": 
                text = event.data['speechResult']['speech']; 
                app.logger.info("Recognition completed, text=%s, context=%s", text, event.data.get('operationContext'))
                # call_connection_client.hang_up(is_for_everyone=True)
            # handle_play(call_connection_client=call_connection_client, text_to_play="Recognized successfully",context="textSourceContext")
            call_connection_client.hang_up(is_for_everyone=True)
            
        elif event.type == "Microsoft.Communication.RecognizeFailed":
            # failedContext = event.data['operationContext']
            app.logger.info("Recognize Failed: data=%s", event.data) 
            # if(failedContext and failedContext == RETRY_CONTEXT):
            #     handle_play(call_connection_client=call_connection_client, text_to_play=NO_RESPONSE)
            # else:
            #     resultInformation = event.data['resultInformation']
            #     app.logger.info("Encountered error during recognize, message=%s, code=%s, subCode=%s", 
            #                     resultInformation['message'], 
            #                     resultInformation['code'],
            #                     resultInformation['subCode'])
            #     if(resultInformation['subCode'] in[8510, 8510]):
            #         textToPlay =CUSTOMER_QUERY_TIMEOUT
            #     else :
            #         textToPlay =INVALID_AUDIO
            
            resultInformation = event.data['resultInformation']
            app.logger.info("Encountered error during recognize, message=%s, code=%s, subCode=%s", 
                                resultInformation['message'], 
                                resultInformation['code'],
                                resultInformation['subCode'])
                # get_media_recognize_options(
                #     call_connection_client=call_connection_client,
                #     text_to_play=textToPlay, 
                #     target_participant=target_participant,
                #     choices=get_choices(),context=RETRY_CONTEXT)
            # call_connection_client.hang_up(is_for_everyone=True)
            handle_play(call_connection_client=call_connection_client, text_to_play="Recognized Failed",context="textSourceContext")

        elif event.type in ["Microsoft.Communication.PlayCompleted"]:
            app.logger.info("Play completed: data=%s", event.data) 
            app.logger.info("Terminating call")
            call_connection_client.hang_up(is_for_everyone=True)
        elif event.type in ["Microsoft.Communication.PlayFailed"]:
            app.logger.info("Play Failed: data=%s", event.data) 
            resultInformation = event.data['resultInformation']
            app.logger.info("Encountered error during play, message=%s, code=%s, subCode=%s", 
                                resultInformation['message'], 
                                resultInformation['code'],
                                resultInformation['subCode'])
            call_connection_client.hang_up(is_for_everyone=True)
        return Response(status=200)

# GET endpoint to render the menus
@app.route('/')
def index_handler():
    return render_template("index.html")


if __name__ == '__main__':
    app.logger.setLevel(INFO)
    app.run(port=8080)
