from flask import Flask, Response, request
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

# Your ACS resource PSTN number will act as source number to start outbound call
ACS_PSTN_SOURCE_NUMBER = "<ACS_PSTN_SOURCE_NUMBER>"

# Target phone number you want to receive the call.
TARGET_PHONE_NUMBER = "<TARGET_PHONE_NUMBER>"

# Callback events URL to handle callback events, such as CallConnected.
CALLBACK_HOST = "<CALLBACK_HOST_WITH_PROTOCOL>"
CALLBACK_EVENTS_URL = CALLBACK_HOST + "/callback_events"

# These recorded prompts must be uploaded to publicly available URLs
MAIN_MENU_PROMPT_URL = CALLBACK_HOST + "/audio/PROMPT_MAIN_MENU.wav"
RECORDING_STARTED_PROMPT_URL = CALLBACK_HOST + "/audio/PROMPT_PLAY_RECORDING_STARTED.wav"
RETRY_PROMPT_URL = CALLBACK_HOST + "/audio/PROMPT_RETRY.wav"
GOODBYE_PROMPT_URL = CALLBACK_HOST + "/audio/PROMPT_GOODBYE.wav"


@app.route('/')
def index_handler():
    welcome_message = "<a href='/create_outbound_call'>Make outbound call to {0}</a><br><br>"
    index_str = welcome_message.format(TARGET_PHONE_NUMBER)
    return index_str


@app.route('/create_outbound_call')
def create_outbound_call_handler():
    target_participant = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
    source_caller_id_number = PhoneNumberIdentifier(ACS_PSTN_SOURCE_NUMBER)
    call_invite = CallInvite(target=target_participant, source_caller_id_number=source_caller_id_number)
    call_automation_client = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)
    create_call_result = call_automation_client.create_call(call_invite, CALLBACK_EVENTS_URL)
    return "Created call with connection id: " + create_call_result.call_connection_id


@app.route('/callback_events', methods=['POST'])
def callback_events_handler():
    for event_dict in request.json:
        # Parsing callback events
        event = CloudEvent.from_dict(event_dict)
        call_connection_id = event.data['callConnectionId']
        call_connection_client = CallConnectionClient.from_connection_string(ACS_CONNECTION_STRING, call_connection_id)
        app.logger.info("%s event received for call connection id: %s", event.type, call_connection_id)

        # Triggering DTMF recognize API after call is connected
        # or retry flow is triggered which will be identified using operationContext of PlayCompleted event
        if event.type == "Microsoft.Communication.CallConnected" or \
                (event.type == "Microsoft.Communication.PlayCompleted" and
                 'operationContext' in event.data and event.data['operationContext'] == "RESTART_RECOGNIZE"):
            app.logger.info("Starting recognize")
            target_participant = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
            main_menu_prompt = FileSource(MAIN_MENU_PROMPT_URL)
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
            choice = event.data['collectTonesResult']['tones'][0]
            app.logger.info("Received choice %s", choice)
            # Handle 1-3 choices as per business requirements.
            # ...
            # Start recording and again trigger recognize by setting operation_context as RESTART_RECOGNIZE
            if choice == DtmfTone.FOUR:
                app.logger.info("Starting recording")
                server_call_id = call_connection_client.get_call_properties().server_call_id
                call_automation_client = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)
                call_automation_client.start_recording(call_locator=ServerCallLocator(server_call_id),
                                                       recording_state_callback_url=CALLBACK_EVENTS_URL)
                recording_started_prompt = FileSource(RECORDING_STARTED_PROMPT_URL)
                call_connection_client.play_media_to_all(recording_started_prompt, operation_context="RESTART_RECOGNIZE")

            # Play goodbye prompt with operation context GOODBYE_PLAYED.
            elif choice == DtmfTone.FIVE:
                app.logger.info("Playing goodbye prompt")
                goodbye_prompt = FileSource(GOODBYE_PROMPT_URL)
                call_connection_client.play_media_to_all(goodbye_prompt, operation_context="GOODBYE_PLAYED")

            # Play retry prompt with operation_context as RESTART_RECOGNIZE.
            else:
                app.logger.info("Playing retry prompt")
                retry_prompt = FileSource(RETRY_PROMPT_URL)
                call_connection_client.play_media_to_all(retry_prompt, operation_context="RESTART_RECOGNIZE")

        # DTMF recognize failed due to timeout, play retry prompt with operation_context as RESTART_RECOGNIZE.
        elif event.type == "Microsoft.Communication.RecognizeFailed":
            app.logger.info("Recognize timed out, playing retry prompt")
            retry_prompt = FileSource(RETRY_PROMPT_URL)
            call_connection_client.play_media_to_all(retry_prompt, operation_context="RESTART_RECOGNIZE")

        # Terminating call once goodbye prompt play is completed.
        elif event.type == "Microsoft.Communication.PlayCompleted" and \
                'operationContext' in event.data and event.data['operationContext'] == "GOODBYE_PLAYED":
            app.logger.info("Terminating call")
            call_connection_client.hang_up(is_for_everyone=True)

        return Response(status=200)


if __name__ == '__main__':
    app.logger.setLevel(INFO)
    app.run()
