from flask import Flask, Response, request, jsonify
from logging import INFO
from azure.communication.callautomation import (
    CallAutomationClient,
    CallConnectionClient,
    PhoneNumberIdentifier,
    ServerCallLocator,
    CallInvite,
    DtmfTone,
    RecognizeInputType,
    FileSource)
from azure.core.messaging import CloudEvent

app = Flask(__name__, static_folder="audio", static_url_path="/audio")

# Your ACS resource connection string
ACS_CONNECTION_STRING = "<ACS_CONNECTION_STRING>"

# Your ACS resource phone number will act as source number to start outbound call
ACS_PHONE_NUMBER = "<ACS_PHONE_NUMBER>"

# Target phone number you want to receive the call.
TARGET_PHONE_NUMBER = "<TARGET_PHONE_NUMBER>"

# Callback events URL to handle callback events.
CALLBACK_URI_HOST = "<CALLBACK_URI_HOST_WITH_PROTOCOL>"
CALLBACK_EVENTS_URI = CALLBACK_URI_HOST + "/api/callbacks"

# These recorded prompts must be uploaded to publicly available URIs
MAIN_MENU_PROMPT_URI = CALLBACK_URI_HOST + "/audio/MainMenu.wav"
CONFIRMED_PROMPT_URI = CALLBACK_URI_HOST + "/audio/Confirmed.wav"
GOODBYE_PROMPT_URI = CALLBACK_URI_HOST + "/audio/Goodbye.wav"


@app.route('/api/outboundCall')
def create_outbound_call_handler():
    target_participant = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
    source_caller_id_number = PhoneNumberIdentifier(ACS_PHONE_NUMBER)
    call_invite = CallInvite(target=target_participant, source_caller_id_number=source_caller_id_number)
    call_automation_client = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)
    create_call_result = call_automation_client.create_call(call_invite, CALLBACK_EVENTS_URI)
    return "Created call with connection id: " + create_call_result.call_connection_id


@app.route('/api/callbacks', methods=['POST'])
def callback_events_handler():
    for event_dict in request.json:
        # Parsing callback events
        event = CloudEvent.from_dict(event_dict)
        call_connection_id = event.data['callConnectionId']
        call_connection_client = CallConnectionClient.from_connection_string(ACS_CONNECTION_STRING, call_connection_id)
        app.logger.info("%s event received for call connection id: %s", event.type, call_connection_id)

        # Starting recording and triggering DTMF recognize API after call is connected
        if event.type == "Microsoft.Communication.CallConnected":
            app.logger.info("Starting recording")
            call_automation_client = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)
            call_automation_client.start_recording(call_locator=ServerCallLocator(event.data['serverCallId']))

            app.logger.info("Starting recognize")
            target_participant = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
            main_menu_prompt = FileSource(MAIN_MENU_PROMPT_URI)
            call_connection_client.start_recognizing_media(input_type=RecognizeInputType.DTMF,
                                                           target_participant=target_participant,
                                                           play_prompt=main_menu_prompt,
                                                           interrupt_prompt=True,
                                                           initial_silence_timeout=10,
                                                           dtmf_inter_tone_timeout=10,
                                                           dtmf_max_tones_to_collect=1,
                                                           dtmf_stop_tones=[DtmfTone.POUND])

        # Handle different scenarios based on DTMF tone received in RecognizeCompleted event
        elif event.type == "Microsoft.Communication.RecognizeCompleted":
            selected_tone = event.data['collectTonesResult']['tones'][0]
            app.logger.info("Received DTMF tone %s", selected_tone)

            if selected_tone == DtmfTone.ONE:
                app.logger.info("Playing confirmed prompt")
                call_connection_client.play_media_to_all(FileSource(CONFIRMED_PROMPT_URI))
            elif selected_tone == DtmfTone.TWO:
                app.logger.info("Playing goodbye prompt")
                call_connection_client.play_media_to_all(FileSource(GOODBYE_PROMPT_URI))
            else:
                app.logger.info("Invalid selection, terminating call")
                call_connection_client.hang_up(is_for_everyone=True)

        elif event.type in ["Microsoft.Communication.PlayCompleted", "Microsoft.Communication.RecognizeFailed"]:
            app.logger.info("Terminating call")
            call_connection_client.hang_up(is_for_everyone=True)

        return Response(status=200)


@app.route('/')
def index_handler():
    welcome_message = "<a href='/api/outboundCall'>Make outbound call to {0}</a><br><br>"
    return welcome_message.format(TARGET_PHONE_NUMBER)


if __name__ == '__main__':
    app.logger.setLevel(INFO)
    app.run(port=8080)
