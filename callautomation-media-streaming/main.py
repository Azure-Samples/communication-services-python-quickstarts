
import ast
from pyexpat import model
import uuid
from urllib.parse import urlencode, urljoin
from azure.eventgrid import EventGridEvent, SystemEventNames
import requests
from flask import Flask, Response, request, json
from logging import INFO
import re
from azure.communication.callautomation import (
    CallAutomationClient,
    MediaStreamingAudioChannelType,
    MediaStreamingTransportType,
    MediaStreamingContentType,
    MediaStreamingOptions
    )
from azure.core.messaging import CloudEvent
import time
# import openai

# from openai.api_resources import (
#     ChatCompletion
# )

# Your ACS resource connection string
ACS_CONNECTION_STRING = "<ACS_CONNECTION_STRING>"

# Transport url
TRANSPORT_URL = "<WEBSOCKET_URL>"

# Callback events URI to handle callback events.
CALLBACK_URI_HOST = "<CALLBACK_URI>"
CALLBACK_EVENTS_URI = CALLBACK_URI_HOST + "/api/callbacks"

call_automation_client = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)

app = Flask(__name__)

def handle_hangup(call_connection_id):     
    call_automation_client.get_call_connection(call_connection_id).hang_up(is_for_everyone=True)

@app.route("/api/incomingCall",  methods=['POST'])
def incoming_call_handler():
    app.logger.info("incoming event data")
    for event_dict in request.json:
        event = EventGridEvent.from_dict(event_dict)
        app.logger.info("incoming event data --> %s", event.data)
        if event.event_type == SystemEventNames.EventGridSubscriptionValidationEventName:
            app.logger.info("Validating subscription")
            validation_code = event.data['validationCode']
            validation_response = {'validationResponse': validation_code}
            return Response(response=json.dumps(validation_response), status=200)
        elif event.event_type =="Microsoft.Communication.IncomingCall":
            app.logger.info("Incoming call received: data=%s", 
                            event.data)  
            if event.data['from']['kind'] =="phoneNumber":
                caller_id =  event.data['from']["phoneNumber"]["value"]
            else :
                caller_id =  event.data['from']['rawId'] 
            app.logger.info("incoming call handler caller id: %s",
                            caller_id)
            incoming_call_context=event.data['incomingCallContext']
            guid =uuid.uuid4()
            query_parameters = urlencode({"callerId": caller_id})
            callback_uri = f"{CALLBACK_EVENTS_URI}/{guid}?{query_parameters}"

            app.logger.info("callback url: %s",  callback_uri)

            media_streaming_configuration=MediaStreamingOptions(
                        transport_url=TRANSPORT_URL,
                        transport_type=MediaStreamingTransportType.WEBSOCKET,
                        content_type=MediaStreamingContentType.AUDIO,
                        audio_channel_type=MediaStreamingAudioChannelType.MIXED,
                        start_media_streaming=True
                        )
            answer_call_result = call_automation_client.answer_call(incoming_call_context=incoming_call_context,
                                                                    media_streaming=media_streaming_configuration,
                                                                    callback_url=callback_uri)
            app.logger.info("Answered call for connection id: %s",
                            answer_call_result.call_connection_id)
            return Response(status=200)
            
@app.route("/api/callbacks/<contextId>", methods=["POST"])
def handle_callback(contextId):    
    try:        
        global caller_id , call_connection_id
        app.logger.info("Request Json: %s", request.json)
        for event_dict in request.json:       
            event = CloudEvent.from_dict(event_dict)
            call_connection_id = event.data['callConnectionId']

            app.logger.info("%s event received for call connection id: %s, correlation id: %s", 
                            event.type, call_connection_id, event.data["correlationId"])
            caller_id = request.args.get("callerId").strip()
            if "+" not in caller_id:
                caller_id="+".strip()+caller_id.strip()

            app.logger.info("call connected : data=%s", event.data)
            if event.type == "Microsoft.Communication.CallConnected":
               
                global call_properties
                call_properties = call_automation_client.get_call_connection(call_connection_id).get_call_properties()
                app.logger.info("Transcription subscription--->=%s", call_properties.transcription_subscription)
 
            elif event.type == "Microsoft.Communication.PlayCompleted":
                context=event.data['operationContext']    
                app.logger.info("Play completed: context=%s", event.data['operationContext'])
            elif event.type == "Microsoft.Communication.MediaStreamingStarted":
                app.logger.info("Received MediaStreamingStarted event.")
            elif event.type == "Microsoft.Communication.MediaStreamingStopped":
                app.logger.info("Received MediaStreamingStopped event.")
            elif event.type == "Microsoft.Communication.MediaStreamingFailed":
                app.logger.info("Received MediaStreamingFailed event.")
                resultInformation = event.data['resultInformation']
                app.logger.info("Encountered error during Media streaming, message=%s, code=%s, subCode=%s", 
                                    resultInformation['message'], 
                                    resultInformation['code'],
                                    resultInformation['subCode'])
        return Response(status=200) 
    except Exception as ex:
        app.logger.info("error in event handling")

@app.route("/")
def hello():
    return "Hello ACS CallAutomation!..test"

if __name__ == '__main__':
    app.logger.setLevel(INFO)
    app.run(port=8080)
