
from pyexpat import model
import uuid
from urllib.parse import urlencode, urljoin
from azure.eventgrid import EventGridEvent, SystemEventNames
import requests
from flask import Flask, Response, request, json,render_template,redirect
from logging import INFO
import re
from azure.communication.callautomation import (
    CallAutomationClient,
    PhoneNumberIdentifier,
    RecognizeInputType,
    TextSource,
    CommunicationUserIdentifier
    )
from azure.core.messaging import CloudEvent

COMMUNICATION_USR_ID = ""

# Your ACS resource connection string
ACS_CONNECTION_STRING = ""

# Cognitive service endpoint
COGNITIVE_SERVICE_ENDPOINT=""

# Agent Phone Number
TARGET_PHONE_NUMBER=""

ACS_PHONE_NUMBER=""

# Callback events URI to handle callback events.
CALLBACK_URI_HOST = ""

CALLBACK_EVENTS_URI = CALLBACK_URI_HOST + "/api/callbacks"


TEMPLATE_FILES_PATH = "template"

HELLO_PROMPT = "Welcome to the Contoso Utilities. Thank you!"

call_automation_client = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)

recording_id = None
recording_chunks_location = []

app = Flask(__name__,
            template_folder=TEMPLATE_FILES_PATH)

@app.route('/createCall')
def outbound_call_handler():
    target_participant = CommunicationUserIdentifier(COMMUNICATION_USR_ID)
    # source_caller = PhoneNumberIdentifier(ACS_PHONE_NUMBER)
    call_connection_properties = call_automation_client.create_call(target_participant, 
                                                                    CALLBACK_URI_HOST,
                                                                    cognitive_services_endpoint=COGNITIVE_SERVICE_ENDPOINT
                                                                    )
    app.logger.info("Created call with connection id: %s", call_connection_properties.call_connection_id)
    return redirect("/")

def handle_recognize(replyText,callerId,call_connection_id,context=""):
    play_source = TextSource(text=replyText, voice_name="en-US-NancyNeural")    
    recognize_result=call_automation_client.get_call_connection(call_connection_id).start_recognizing_media( 
    input_type=RecognizeInputType.SPEECH,
    target_participant=PhoneNumberIdentifier(callerId), 
    end_silence_timeout=10, 
    play_prompt=play_source,
    operation_context=context)
    app.logger.info("handle_recognize : data=%s",recognize_result) 

def handle_play(call_connection_id, text_to_play, context):     
    play_source = TextSource(text=text_to_play, voice_name= "en-US-NancyNeural") 
    call_automation_client.get_call_connection(call_connection_id).play_media_to_all(play_source,
                                                                                     operation_context=context)
    
def handle_hangup(call_connection_id):     
    call_automation_client.get_call_connection(call_connection_id).hang_up(is_for_everyone=True)


@app.route("/api/incomingCall",  methods=['POST'])
def incoming_call_handler():
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

                answer_call_result = call_automation_client.answer_call(incoming_call_context=incoming_call_context,
                                                                        cognitive_services_endpoint=COGNITIVE_SERVICE_ENDPOINT,
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

            app.logger.info("%s event received for call connection id: %s", event.type, call_connection_id)
            caller_id = request.args.get("callerId").strip()
            if "+" not in caller_id:
                caller_id="+".strip()+caller_id.strip()

            app.logger.info("call connected : data=%s", event.data)
            if event.type == "Microsoft.Communication.CallConnected":
                  app.logger.info("Call connected")
                  handle_play(call_connection_id,HELLO_PROMPT,"helloContext")
                 
            elif event.type == "Microsoft.Communication.RecognizeCompleted":
                 app.logger.info("Recognition completed")

            elif event.type == "Microsoft.Communication.RecognizeFailed":
                resultInformation = event.data['resultInformation']
                reasonCode = resultInformation['subCode']
                context=event.data['operationContext']   
            elif event.type == "Microsoft.Communication.PlayCompleted":
                context=event.data['operationContext']
                app.logger.info(context)
                handle_hangup(call_connection_id)
            elif event.type == "Microsoft.Communication.CallTransferAccepted":
                app.logger.info(f"Call transfer accepted event received for connection id: {call_connection_id}")   
             
            elif event.type == "Microsoft.Communication.CallTransferFailed":
                app.logger.info(f"Call transfer failed event received for connection id: {call_connection_id}")
                resultInformation = event.data['resultInformation']
                sub_code = resultInformation['subCode']
                # check for message extraction and code
                app.logger.info(f"Encountered error during call transfer, message=, code=, subCode={sub_code}")   
            elif event.type == "Microsoft.Communication.CallDisconnected":             
                app.logger.info(f"Received CallDisconnected event for connection id: {call_connection_id}")
        return Response(status=200) 
    except Exception as ex:
        app.logger.info("error in event handling")

# GET endpoint to render the menus
@app.route('/')
def index_handler():
    return render_template("index.html")

if __name__ == '__main__':
    app.logger.setLevel(INFO)
    app.run(port=8080)
