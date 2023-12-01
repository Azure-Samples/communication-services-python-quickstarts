from azure.eventgrid import EventGridEvent, SystemEventNames
from flask import Flask, Response, request, json, send_file, render_template, redirect
from logging import INFO
from azure.communication.callautomation import (
    CallAutomationClient,
    CallConnectionClient,
    PhoneNumberIdentifier,
    RecognizeInputType,
    RecognitionChoice,
    DtmfTone,
    TextSource)
from azure.core.messaging import CloudEvent

# Your ACS resource connection string
ACS_CONNECTION_STRING = "<ACS_CONNECTION_STRING>"

# Your ACS resource phone number will act as source number to start outbound call
ACS_PHONE_NUMBER = "<ACS_PHONE_NUMBER>"

# Target phone number you want to receive the call.
TARGET_PHONE_NUMBER = "<TARGET_PHONE_NUMBER>"

# Callback events URI to handle callback events.
CALLBACK_URI_HOST = "<CALLBACK_URI_HOST_WITH_PROTOCOL>"
CALLBACK_EVENTS_URI = CALLBACK_URI_HOST + "/api/callbacks"
COGNITIVE_SERVICES_ENDPOINT = "<COGNITIVE_SERVICES_ENDPOINT>"

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

call_automation_client = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)

app = Flask(__name__,
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
     
def handle_play(call_connection_client: CallConnectionClient, text_to_play: str):
        play_source = TextSource(text=text_to_play, voice_name=SPEECH_TO_TEXT_VOICE) 
        call_connection_client.play_media_to_all(play_source)

# GET endpoint to place phone call
@app.route('/outboundCall')
def outbound_call_handler():
    target_participant = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
    source_caller = PhoneNumberIdentifier(ACS_PHONE_NUMBER)
    call_connection_properties = call_automation_client.create_call(target_participant, 
                                                                    CALLBACK_EVENTS_URI,
                                                                    cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT,
                                                                    source_caller_id_number=source_caller)
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
            app.logger.info("Starting recognize")
            get_media_recognize_choice_options(
                call_connection_client=call_connection_client,
                text_to_play=MAIN_MENU, 
                target_participant=target_participant,
                choices=get_choices(),context="")
            
        # Perform different actions based on DTMF tone received from RecognizeCompleted event
        elif event.type == "Microsoft.Communication.RecognizeCompleted":
            app.logger.info("Recognize completed: data=%s", event.data) 
            if event.data['recognitionType'] == "choices": 
                 label_detected = event.data['choiceResult']['label']; 
                 phraseDetected = event.data['choiceResult']['recognizedPhrase']; 
                 app.logger.info("Recognition completed, labelDetected=%s, phraseDetected=%s, context=%s", label_detected, phraseDetected, event.data.get('operationContext'))
                 if label_detected == CONFIRM_CHOICE_LABEL:
                    text_to_play = CONFIRMED_TEXT
                 else:
                    text_to_play = CANCEL_TEXT
                 handle_play(call_connection_client=call_connection_client, text_to_play=text_to_play)

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

        elif event.type in ["Microsoft.Communication.PlayCompleted", "Microsoft.Communication.PlayFailed"]:
            app.logger.info("Terminating call")
            call_connection_client.hang_up(is_for_everyone=True)

        return Response(status=200)

# GET endpoint to render the menus
@app.route('/')
def index_handler():
    return render_template("index.html")


if __name__ == '__main__':
    app.logger.setLevel(INFO)
    app.run(port=8080)
