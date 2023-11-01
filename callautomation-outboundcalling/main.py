from azure.eventgrid import EventGridEvent, SystemEventNames
from flask import Flask, Response, request, json, send_file, render_template, redirect
from logging import INFO
from azure.communication.callautomation import (
    CallAutomationClient,
    CallConnectionClient,
    PhoneNumberIdentifier,
    ServerCallLocator,
    CallInvite,
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

TEMPLATE_FILES_PATH = "template"

# Prompts for text to speech
SpeechToTextVoice = "en-US-NancyNeural"
MainMenu = "Hello this is Contoso Bank, we’re calling in regard to your appointment tomorrow at 9am to open a new account. Please confirm if this time is still suitable for you or if you would like to cancel. This call is recorded for quality purposes."
ConfirmedText = "Thank you for confirming your appointment tomorrow at 9am, we look forward to meeting with you."
CancelText = "Your appointment tomorrow at 9am has been cancelled. Please call the bank directly if you would like to rebook for another date and time."
CustomerQueryTimeout = "I’m sorry I didn’t receive a response, please try again."
NoResponse = "I didn't receive an input, we will go ahead and confirm your appointment. Goodbye"
InvalidAudio = "I’m sorry, I didn’t understand your response, please try again."
ConfirmChoiceLabel = "Confirm"
CancelChoiceLabel = "Cancel"
RetryContext = "retry"

call_automation_client = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)
recording_id = None
recording_chunks_location = []

app = Flask(__name__,
            template_folder=TEMPLATE_FILES_PATH)

def get_choices():
    choices = [
                RecognitionChoice(label = ConfirmChoiceLabel, phrases= ["Confirm", "First", "One"], tone = DtmfTone.ONE),
                RecognitionChoice(label = CancelChoiceLabel, phrases= ["Cancel", "Second", "Two"], tone = DtmfTone.TWO)
            ]
    return choices

def get_media_recognize_choice_options(call_connection_client: CallConnectionClient, text_to_play: str, target_participant:str, choices: any, context: str):
     play_source =  TextSource (text= text_to_play, voice_name= SpeechToTextVoice)
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
        play_source = TextSource(text=text_to_play, voice_name=SpeechToTextVoice) 
        call_connection_client.play_media_to_all(play_source)

# GET endpoint to place phone call
@app.route('/outboundCall')
def outbound_call_handler():
    target_participant = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
    source_caller = PhoneNumberIdentifier(ACS_PHONE_NUMBER)
    call_invite = CallInvite(target=target_participant, source_caller_id_number=source_caller)
    call_connection_properties = call_automation_client.create_call(call_invite, CALLBACK_EVENTS_URI,
                                                                    cognitive_services_endpoint="https://cognitive-service-waferwire.cognitiveservices.azure.com/")
    app.logger.info("Created call with connection id: %s", call_connection_properties.call_connection_id)
    return redirect("/")


# POST endpoint to handle callback events
@app.route('/api/callbacks', methods=['POST'])
def callback_events_handler():
    global recording_id
    for event_dict in request.json:
        # Parsing callback events
        event = CloudEvent.from_dict(event_dict)
        call_connection_id = event.data['callConnectionId']
        app.logger.info("%s event received for call connection id: %s", event.type, call_connection_id)
        call_connection_client = call_automation_client.get_call_connection(call_connection_id)
        target_participant = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)

        # Starting recording and triggering DTMF recognize API after call is connected
        if event.type == "Microsoft.Communication.CallConnected":
            app.logger.info("Starting recording")
            recording_properties = call_automation_client.start_recording(ServerCallLocator(event.data['serverCallId']))
            recording_id = recording_properties.recording_id

            app.logger.info("Starting recognize")
           
            get_media_recognize_choice_options(
                call_connection_client=call_connection_client,
                text_to_play=MainMenu, 
                target_participant=target_participant,
                choices=get_choices(),context="")
            

        # Perform different actions based on DTMF tone received from RecognizeCompleted event
        elif event.type == "Microsoft.Communication.RecognizeCompleted":
            app.logger.info("Recognize completed: data=%s", event.data) 
            if event.data['recognitionType'] == "choices": 
                 labelDetected = event.data['choiceResult']['label']; 
                 phraseDetected = event.data['choiceResult']['recognizedPhrase']; 
                 app.logger.info("Recognition completed, labelDetected=%s, phraseDetected=%s, context=%s", labelDetected, phraseDetected, event.data.get('operationContext'))
                 if labelDetected == ConfirmChoiceLabel:
                    textToPlay = ConfirmedText
                 else:
                    textToPlay = CancelText
                 handle_play(call_connection_client=call_connection_client, text_to_play=textToPlay)

        elif event.type == "Microsoft.Communication.RecognizeFailed":
            failedContext = event.data['operationContext']
            if(failedContext and failedContext == RetryContext):
                handle_play(call_connection_client=call_connection_client, text_to_play=NoResponse)
            else:
                resultInformation = event.data['resultInformation']
                app.logger.info("Encountered error during recognize, message=%s, code=%s, subCode=%s", 
                                resultInformation['message'], 
                                resultInformation['code'],
                                resultInformation['subCode'])
                if(resultInformation['subCode'] in[8510, 8510]):
                    textToPlay =CustomerQueryTimeout
                else :
                    textToPlay =InvalidAudio
                
                get_media_recognize_choice_options(
                    call_connection_client=call_connection_client,
                    text_to_play=CustomerQueryTimeout, 
                    target_participant=target_participant,
                    choices=get_choices(),context=RetryContext)

        elif event.type in ["Microsoft.Communication.PlayCompleted", "Microsoft.Communication.PlayFailed"]:
            app.logger.info("Terminating call")
            call_automation_client.stop_recording(recording_id)
            call_connection_client.hang_up(is_for_everyone=True)

        return Response(status=200)

# POST endpoint to receive recording events
@app.route('/api/recordingFileStatus', methods=['POST'])
def recording_file_status_handler():
    for event_dict in request.json:
        event = EventGridEvent.from_dict(event_dict)
        app.logger.info("Event received: %s", event.event_type)
        if event.event_type == SystemEventNames.EventGridSubscriptionValidationEventName:
            app.logger.info("Validating subscription")
            validation_code = event.data['validationCode']
            validation_response = {'validationResponse': validation_code}
            return Response(response=json.dumps(validation_response), status=200)
        elif event.event_type == SystemEventNames.AcsRecordingFileStatusUpdatedEventName:
            global recording_chunks_location
            recording_chunks_location.clear()
            for recording_chunks in event.data['recordingStorageInfo']['recordingChunks']:
                recording_chunks_location.append(recording_chunks['contentLocation'])
        return Response(status=200)


# GET endpoint to download call recording
@app.route('/download')
def recording_download_handler():
    with open("recording.wav", 'wb') as recording_file:
        for recording_chunk in recording_chunks_location:
            chunk_stream = call_automation_client.download_recording(recording_chunk)
            chunk_data = chunk_stream.read()
            if chunk_data:
                recording_file.write(chunk_data)
    return send_file(recording_file.name, mimetype="audio/wav", as_attachment=True, download_name=recording_file.name)


# GET endpoint to render the menus
@app.route('/')
def index_handler():
    return render_template("index.html")


if __name__ == '__main__':
    app.logger.setLevel(INFO)
    app.run(port=8080)
