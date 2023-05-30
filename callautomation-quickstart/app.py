from flask import Flask, request, redirect, Response
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
import json

app = Flask(__name__)

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
MAIN_MENU_PROMPT_URL = "<MAIN_MENU_WAV_FILE_URL>"

CALL_CONNECTION_ID = None
CALLBACK_EVENTS = []

WELCOME_TEMPLATE_STR = """
    <a href="/create_call">Make outbound call to <TARGET_PHONE_NUMBER></a><br><br>
    <a href="/callback_events" target="_blank">Received callback events</a>
    """
MENU_TEMPLATE_STR = """
    Call connected with connection id: <CALL_CONNECTION_ID><br><br>
    <a href="/record_call?call_connection_id=<CALL_CONNECTION_ID>">Record call</a><br>
    <a href="/play_audio?call_connection_id=<CALL_CONNECTION_ID>">Play welcome message from file</a><br>
    <a href="/recognize_dtmf?call_connection_id=<CALL_CONNECTION_ID>">Recognize DTMF events</a><br>
    <a href="/hangup_call?call_connection_id=<CALL_CONNECTION_ID>">Hang up call</a><br><br>
    <a href="/callback_events" target="_blank">Received callback events</a>
    """


@app.route('/')
def index_handler():
    if "<CALL_CONNECTION_ID>" in MENU_TEMPLATE_STR:
        index_str = WELCOME_TEMPLATE_STR.replace("<TARGET_PHONE_NUMBER>", TARGET_PHONE_NUMBER)
    else:
        index_str = MENU_TEMPLATE_STR
    return index_str


@app.route('/create_call')
def create_call_handler():
    target_participant = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
    source_caller_id_number = PhoneNumberIdentifier(ACS_PSTN_SOURCE_NUMBER)
    call_invite = CallInvite(target=target_participant, source_caller_id_number=source_caller_id_number)
    call_automation_client = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)
    call_connection_properties = call_automation_client.create_call(call_invite, CALLBACK_EVENTS_URL)
    global MENU_TEMPLATE_STR, CALL_CONNECTION_ID
    CALL_CONNECTION_ID = call_connection_properties.call_connection_id
    MENU_TEMPLATE_STR = MENU_TEMPLATE_STR.replace("<CALL_CONNECTION_ID>", CALL_CONNECTION_ID)
    return redirect("/")


@app.route('/record_call')
def record_call():
    call_connection_id = request.args.get('call_connection_id')
    server_call_id = CallConnectionClient.from_connection_string(ACS_CONNECTION_STRING,
                                                                 call_connection_id).get_call_properties().server_call_id
    call_automation_client = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)
    call_automation_client.start_recording(call_locator=ServerCallLocator(server_call_id),
                                           recording_state_callback_url=CALLBACK_EVENTS_URL)
    return redirect("/")


@app.route('/play_audio')
def play_audio_handler():
    call_connection_id = request.args.get('call_connection_id')
    call_connection_client = CallConnectionClient.from_connection_string(ACS_CONNECTION_STRING, call_connection_id)
    file_source = FileSource(MAIN_MENU_PROMPT_URL)
    call_connection_client.play_media_to_all(file_source)
    return redirect("/")


@app.route('/recognize_dtmf')
def recognize_dtmf_handler():
    call_connection_id = request.args.get('call_connection_id')
    target_participant = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
    file_source = FileSource(MAIN_MENU_PROMPT_URL)
    call_connection_client = CallConnectionClient.from_connection_string(ACS_CONNECTION_STRING, call_connection_id)
    call_connection_client.start_recognizing_media(input_type=RecognizeInputType.DTMF,
                                                   target_participant=target_participant,
                                                   play_prompt=file_source,
                                                   interrupt_prompt=True,
                                                   initial_silence_timeout=10,
                                                   dtmf_inter_tone_timeout=10,
                                                   dtmf_max_tones_to_collect=1,
                                                   dtmf_stop_tones=[DtmfTone.POUND])
    return redirect("/")


@app.route('/hangup_call')
def hangup_call_handler():
    call_connection_id = request.args.get('call_connection_id')
    call_connection_client = CallConnectionClient.from_connection_string(ACS_CONNECTION_STRING, call_connection_id)
    call_connection_client.hang_up(is_for_everyone=True)
    global MENU_TEMPLATE_STR
    MENU_TEMPLATE_STR = MENU_TEMPLATE_STR.replace(CALL_CONNECTION_ID, "<CALL_CONNECTION_ID>")
    return redirect("/")


@app.route('/callback_events', methods=['GET', 'POST'])
def callback_events_handler():
    if request.method == 'POST':
        for event_dict in request.json:
            event = CloudEvent.from_dict(event_dict)
            CALLBACK_EVENTS.append(event)
            return Response(status=200)
    else:
        events = ""
        for event in CALLBACK_EVENTS:
            events = events + str(event.time) + " | " + event.type + " | " + json.dumps(event.data) + "<br>"
        return "Received events: <br><br>" + events


if __name__ == '__main__':
    app.run()
