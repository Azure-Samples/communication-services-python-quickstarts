from flask import Flask, request, Response
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

app = Flask(__name__)

ACS_CONNECTION_STRING = "<ACS_CONNECTION_STRING>"
ACS_PSTN_SOURCE_NUMBER = "<ACS_PSTN_SOURCE_NUMBER>"
TARGET_PHONE_NUMBER = "<TARGET_PHONE_NUMBER>"
CALLBACK_EVENTS_URI = "<CALLBACK_HOST_WITH_PROTOCOL>/callback_events"

MAIN_MENU_PROMPT = FileSource("<MAIN_MENU_WAV_FILE_URL>")
RETRY_PROMPT = FileSource("<RETRY_WAV_FILE_URL>")
GOODBYE_PROMPT = FileSource("<GOODBYE_WAV_FILE_URL>")


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
    call_automation = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)
    create_call_result = call_automation.create_call(call_invite, CALLBACK_EVENTS_URI)
    return "Created call with connection id: " + create_call_result.call_connection_id


@app.route('/callback_events', methods=['POST'])
def callback_events_handler():
    for event_dict in request.json:
        event = CloudEvent.from_dict(event_dict)
        call_connection_id = event.data['callConnectionId']
        call_connection = CallConnectionClient.from_connection_string(ACS_CONNECTION_STRING, call_connection_id)
        if event.type == "Microsoft.Communication.CallConnected" or \
                (event.type == "Microsoft.Communication.PlayCompleted" and event.data['operationContext'] == "RETRY_RECOGNIZE"):
            target_participant = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
            call_connection.start_recognizing_media(input_type=RecognizeInputType.DTMF,
                                                    target_participant=target_participant,
                                                    play_prompt=MAIN_MENU_PROMPT,
                                                    interrupt_prompt=True,
                                                    initial_silence_timeout=10,
                                                    dtmf_inter_tone_timeout=10,
                                                    dtmf_max_tones_to_collect=1,
                                                    dtmf_stop_tones=[DtmfTone.POUND, DtmfTone.ASTERISK])

        elif event.type == "Microsoft.Communication.RecognizeCompleted":
            choice = event.data['collectTonesResult']['tones'][0]

            # Handle 1-3 choices as per business requirements.
            if choice == DtmfTone.FOUR:
                server_call_id = event.data['serverCallId']
                call_automation = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)
                call_automation.start_recording(call_locator=ServerCallLocator(server_call_id),
                                                recording_state_callback_url=CALLBACK_EVENTS_URI)
            elif choice == DtmfTone.FIVE:
                call_connection.play_media_to_all(GOODBYE_PROMPT, operation_context="GOODBYE_DONE")
            else:
                call_connection.play_media_to_all(RETRY_PROMPT, operation_context="RETRY_RECOGNIZE")

        elif event.type == "Microsoft.Communication.PlayCompleted" and event.data['operationContext'] == "GOODBYE_DONE":
            call_connection.hang_up(is_for_everyone=True)

        return Response(status=200)


if __name__ == '__main__':
    app.run()
