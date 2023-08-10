from azure.eventgrid import EventGridEvent, SystemEventNames
from flask import Flask, Response, request, json, send_file, render_template, redirect
from logging import INFO
from azure.communication.callautomation import (
    CallAutomationClient,
    PhoneNumberIdentifier,
    CallInvite,
    DtmfTone)
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




call_automation_client = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)
c2_target = TARGET_PHONE_NUMBER

app = Flask(__name__,
            template_folder=TEMPLATE_FILES_PATH)


@app.route('/index.html')
def index_handler():
    return render_template("index.html")


@app.route('/outboundCall')
def outbound_call_handler():
    target_participant = PhoneNumberIdentifier(c2_target)
    source_caller = PhoneNumberIdentifier(ACS_PHONE_NUMBER)
    call_invite = CallInvite(target=target_participant, source_caller_id_number=source_caller)
    call_automation_client.create_call(call_invite, CALLBACK_EVENTS_URI)
    app.logger.info("create_call")
    return redirect("/index.html")


@app.route('/api/callbacks', methods=['POST'])
def callback_events_handler():
    for event_dict in request.json:
        event = CloudEvent.from_dict(event_dict)
        call_connection_id = event.data['callConnectionId']
        app.logger.info("Received event %s for call connection id: %s", event.type, call_connection_id)

        if event.type == "Microsoft.Communication.CallConnected":
            # Send DTMF tones
            tones = [ DtmfTone.ONE, DtmfTone.TWO, DtmfTone.THREE ]
            result = call_automation_client.get_call_connection(call_connection_id).send_dtmf_tones(
                tones=tones,
                target_participant=PhoneNumberIdentifier(c2_target),
                operation_context="dtmfs-to-ivr")
            app.logger.info("Send dtmf, result=%s", result)

        if event.type == "Microsoft.Communication.SendDtmfTonesCompleted":
            app.logger.info("Send dtmf succeeded: context=%s", event.data['operationContext']);

        if event.type == "Microsoft.Communication.SendDtmfTonesFailed":
            app.logger.info("Send dtmf failed: result=%s, context=%s", event.data['resultInformation']['message'], event.data['operationContext'])

        return Response(status=200)


if __name__ == '__main__':
    app.logger.setLevel(INFO)
    app.run(port=8080)
