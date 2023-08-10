from azure.eventgrid import EventGridEvent, SystemEventNames
from flask import Flask, Response, request, json, send_file, render_template, redirect
from logging import INFO
from azure.communication.callautomation import (
    CallAutomationClient,
    PhoneNumberIdentifier,
    CommunicationUserIdentifier,
    CallInvite,
    FileSource,
    TextSource,
    SsmlSource,
    VoiceKind,
    RecognizeInputType,
    DtmfTone,
    RecognitionChoice)
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

audioUri = CALLBACK_URI_HOST + "/prompt.wav"

operation = "PlayTextWithKind"


call_automation_client = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)
c2_target = TARGET_PHONE_NUMBER
usePhone = False

if usePhone:
    target_phone_number_identifier = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
    target_participant = target_phone_number_identifier
    caller_phone_number_identifier = PhoneNumberIdentifier(ACS_PHONE_NUMBER)
    call_invite = CallInvite(target=target_phone_number_identifier, source_caller_id_number=caller_phone_number_identifier)
else:
    target_communication_user_identifier = CommunicationUserIdentifier(TARGET_USER_ID)
    target_participant = target_communication_user_identifier
    call_invite = CallInvite(target=target_communication_user_identifier)

app = Flask(__name__,
            template_folder=TEMPLATE_FILES_PATH)


@app.route('/index.html')
def index_handler():
    return render_template("index.html")


@app.route('/outboundCall')
def outbound_call_handler():
    call_automation_client.create_call(target_participant=call_invite, callback_url=CALLBACK_EVENTS_URI, cognitive_services_endpoint=COGNITIVE_SERVICE_ENDPOINT)
    app.logger.info("create_call")
    return redirect("/index.html")


@app.route('/api/callbacks', methods=['POST'])
def callback_events_handler():
    for event_dict in request.json:
        event = CloudEvent.from_dict(event_dict)
        call_connection_id = event.data['callConnectionId']
        app.logger.info("Received event %s for call connection id: %s", event.type, call_connection_id)

        if event.type == "Microsoft.Communication.CallConnected":

            if operation == "PlayFile":
                play_source = FileSource(url=audioUri)
                play_to = [ target_participant ]
                call_automation_client.get_call_connection(call_connection_id).play_media(
                    play_source=play_source,
                    play_to=play_to)
                app.logger.info("Play")
            elif operation == "PlayTextWithKind":
                text_to_play = "Welcome to Contoso"
                # Provide SourceLocale and VoiceKind to select an appropriate voice. SourceLocale or VoiceName needs to be provided.
                # TODO: voice_kind does not work: getting a male voice
                play_source = TextSource(text=text_to_play, source_locale="en-US", voice_kind=VoiceKind.FEMALE)
                play_source = TextSource(text=text_to_play, source_locale="en-US", voice_kind="female")
                play_to = [ target_participant ]
                call_automation_client.get_call_connection(call_connection_id).play_media(
                    play_source=play_source,
                    play_to=play_to)
                app.logger.info("Play")
            elif operation == "PlayTextWithVoice":
                text_to_play = "Welcome to Contoso"
                # Provide VoiceName to select a specific voice. SourceLocale or VoiceName needs to be provided.
                play_source = TextSource(text=text_to_play, voice_name="en-US-ElizabethNeural")
                play_to = [ target_participant ]
                call_automation_client.get_call_connection(call_connection_id).play_media(
                    play_source=play_source,
                    play_to=play_to)
                app.logger.info("Play")
            elif operation == "PlaySSML":
                ssmlToPlay = "<speak version=\"1.0\" xmlns=\"http://www.w3.org/2001/10/synthesis\" xml:lang=\"en-US\"><voice name=\"en-US-JennyNeural\">Hello World!</voice></speak>"
                play_source = SsmlSource(ssml_text=ssmlToPlay)
                play_to = [ target_participant ]
                call_automation_client.get_call_connection(call_connection_id).play_media(
                    play_source=play_source,
                    play_to=play_to)
                app.logger.info("Play")
            elif operation == "PlayToAll":
                text_to_play = "Welcome to Contoso"
                play_source = TextSource(text=text_to_play, voice_name="en-US-ElizabethNeural")
                call_automation_client.get_call_connection(call_connection_id).play_media_to_all(
                    play_source=play_source)
                app.logger.info("Play")
            elif operation == "PlayLoop":
                text_to_play = "Welcome to Contoso"
                play_source = TextSource(text=text_to_play, voice_name="en-US-ElizabethNeural")
                call_automation_client.get_call_connection(call_connection_id).play_media_to_all(
                    play_source=play_source,
                    loop=True)
                app.logger.info("Play")
            elif operation == "PlayWithCache":
                play_source = FileSource(url=audioUri, play_source_cache_id="<playSourceId>")
                play_to = [ target_participant ]
                call_automation_client.get_call_connection(call_connection_id).play_media(
                    play_source=play_source,
                    play_to=play_to)
                app.logger.info("Play")
            elif operation == "CancelMedia":
                call_automation_client.get_call_connection(call_connection_id).cancel_all_media_operations()
                app.logger.info("Cancel, result=%s", result)
            elif operation == "RecognizeDTMF":
                max_tones_to_collect = 3
                text_to_play = "Welcome to Contoso, please enter 3 DTMF."
                play_source = TextSource(text=text_to_play, voice_name="en-US-ElizabethNeural")
                call_automation_client.get_call_connection(call_connection_id).start_recognizing_media(
                    dtmf_max_tones_to_collect=max_tones_to_collect,
                    input_type=RecognizeInputType.DTMF,
                    target_participant=target_participant,
                    initial_silence_timeout=30,
                    play_prompt=play_source,
                    dtmf_inter_tone_timeout=5,
                    interrupt_prompt=True,
                    dtmf_stop_tones=[ DtmfTone.Pound ])
                app.logger.info("Start recognizing")
            elif operation == "RecognizeChoice":
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
                    )
                ]
                text_to_play = "Hello, This is a reminder for your appointment at 2 PM, Say Confirm to confirm your appointment or Cancel to cancel the appointment. Thank you!"
                play_source = TextSource(text=text_to_play, voice_name="en-US-ElizabethNeural")
                call_automation_client.get_call_connection(call_connection_id).start_recognizing_media(
                    input_type=RecognizeInputType.CHOICES,
                    target_participant=target_participant,
                    choices=choices,
                    interrupt_prompt=True,
                    initial_silence_timeout=30,
                    play_prompt=play_source,
                    operation_context="AppointmentReminderMenu")
                app.logger.info("Start recognizing")
            elif operation == "RecognizeSpeech":
                text_to_play = "Hi, how can I help you today?"
                play_source = TextSource(text=text_to_play, voice_name="en-US-ElizabethNeural")
                call_automation_client.get_call_connection(call_connection_id).start_recognizing_media(
                    input_type=RecognizeInputType.SPEECH,
                    target_participant=target_participant,
                    end_silence_timeout=1,
                    play_prompt=play_source,
                    operation_context="OpenQuestionSpeech")
                app.logger.info("Start recognizing")
            elif operation == "RecognizeSpeechOrDtmf":
                max_tones_to_collect = 1
                text_to_play = "Hi, how can I help you today, you can also press 0 to speak to an agent."
                play_source = TextSource(text=text_to_play, voice_name="en-US-ElizabethNeural")
                call_automation_client.get_call_connection(call_connection_id).start_recognizing_media(
                    dtmf_max_tones_to_collect=max_tones_to_collect,
                    input_type=RecognizeInputType.SPEECH_OR_DTMF,
                    target_participant=target_participant,
                    end_silence_timeout=1,
                    play_prompt=play_source,
                    initial_silence_timeout=30,
                    interrupt_prompt=True,
                    operation_context="OpenQuestionSpeechOrDtmf")
                app.logger.info("Start recognizing")

        if event.type == "Microsoft.Communication.PlayCompleted":
            app.logger.info("Play completed, context=%s", event.data.get('operationContext'));

        if event.type == "Microsoft.Communication.PlayFailed":
            app.logger.info("Play failed: data=%s", event.data)

        if event.type == "Microsoft.Communication.PlayCanceled":
            app.logger.info("Play canceled, context=%s", event.data.get('operationContext'))

        if event.type == "Microsoft.Communication.RecognizeCompleted":
            app.logger.info("Recognize completed: data=%s", event.data)
            if event.data['recognitionType'] == "dtmf":
                tones = event.data['dtmfResult']['tones']
                app.logger.info("Recognition completed, tones=%s, context=%s", tones, event.data.get('operationContext'))
            elif event.data['recognitionType'] == "choices":
                labelDetected = event.data['choiceResult']['label'];
                phraseDetected = event.data['choiceResult']['recognizedPhrase'];
                app.logger.info("Recognition completed, labelDetected=%s, phraseDetected=%s, context=%s", labelDetected, phraseDetected, event.data.get('operationContext'));
            elif event.data['recognitionType'] == "speech":
                text = event.data['speechResult']['speech'];
                app.logger.info("Recognition completed, text=%s, context=%s", text, event.data.get('operationContext'));
            else:
                app.logger.info("Recognition completed: data=%s", event.data);
    
        if event.type == "Microsoft.Communication.RecognizeFailed":
            app.logger.info("Recognize failed: data=%s", event.data);
    
        return Response(status=200)


if __name__ == '__main__':
    app.logger.setLevel(INFO)
    app.run(port=8080)
