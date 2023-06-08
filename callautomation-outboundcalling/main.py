from azure.eventgrid import EventGridEvent, SystemEventNames
from flask import Flask, Response, request, json, send_file, render_template, redirect
from logging import INFO
from azure.communication.callautomation import (
    CallAutomationClient,
    PhoneNumberIdentifier,
    ServerCallLocator,
    CallInvite,
    DtmfTone,
    RecognizeInputType,
    FileSource)
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

AUDIO_FILES_PATH = "/audio"
TEMPLATE_FILES_PATH = "template"

# These recorded prompts must be on publicly available URIs
MAIN_MENU_PROMPT_URI = CALLBACK_URI_HOST + AUDIO_FILES_PATH + "/MainMenu.wav"
CONFIRMED_PROMPT_URI = CALLBACK_URI_HOST + AUDIO_FILES_PATH + "/Confirmed.wav"
GOODBYE_PROMPT_URI = CALLBACK_URI_HOST + AUDIO_FILES_PATH + "/Goodbye.wav"
INVALID_PROMPT_URI = CALLBACK_URI_HOST + AUDIO_FILES_PATH + "/Invalid.wav"
TIMEOUT_PROMPT_URI = CALLBACK_URI_HOST + AUDIO_FILES_PATH + "/Timeout.wav"

call_automation_client = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)
recording_id = None
recording_chunks_location = []

app = Flask(__name__,
            static_folder=AUDIO_FILES_PATH.strip("/"),
            static_url_path=AUDIO_FILES_PATH,
            template_folder=TEMPLATE_FILES_PATH)


# GET endpoint to place phone call
@app.route('/outboundCall')
def outbound_call_handler():
    target_participant = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
    source_caller = PhoneNumberIdentifier(ACS_PHONE_NUMBER)
    call_invite = CallInvite(target=target_participant, source_caller_id_number=source_caller)
    call_connection_properties = call_automation_client.create_call(call_invite, CALLBACK_EVENTS_URI)
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

        # Starting recording and triggering DTMF recognize API after call is connected
        if event.type == "Microsoft.Communication.CallConnected":
            app.logger.info("Starting recording")
            recording_properties = call_automation_client.start_recording(ServerCallLocator(event.data['serverCallId']))
            recording_id = recording_properties.recording_id

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

        # Perform different actions based on DTMF tone received from RecognizeCompleted event
        elif event.type == "Microsoft.Communication.RecognizeCompleted":
            selected_tone = event.data['dtmfResult']['tones'][0]
            app.logger.info("Received DTMF tone %s", selected_tone)

            if selected_tone == DtmfTone.ONE:
                app.logger.info("Playing confirmed prompt")
                call_connection_client.play_media_to_all([FileSource(CONFIRMED_PROMPT_URI)])
            elif selected_tone == DtmfTone.TWO:
                app.logger.info("Playing goodbye prompt")
                call_connection_client.play_media_to_all([FileSource(GOODBYE_PROMPT_URI)])
            else:
                app.logger.info("Invalid selection, terminating call")
                call_connection_client.play_media_to_all([FileSource(INVALID_PROMPT_URI)])

        elif event.type == "Microsoft.Communication.RecognizeFailed":
            app.logger.info("Failed to recognize tone")
            call_connection_client.play_media_to_all([FileSource(TIMEOUT_PROMPT_URI)])

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
