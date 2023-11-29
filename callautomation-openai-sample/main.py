
from pyexpat import model
import uuid
from urllib.parse import urlencode, urljoin
from azure.eventgrid import EventGridEvent, SystemEventNames
import requests
from flask import Flask, Response, request, json
from logging import INFO
from azure.communication.callautomation import (
    CallAutomationClient,
    PhoneNumberIdentifier,
    RecognizeInputType,
    TextSource
    )
from azure.core.messaging import CloudEvent
import openai

from openai.api_resources import (
    ChatCompletion
)

# Your ACS resource connection string
ACS_CONNECTION_STRING = "<ACS_CONNECTION_STRING>"

# Cognitive service endpoint
COGNITIVE_SERVICE_ENDPOINT="<COGNITIVE_SERVICE_ENDPOINT>"

# Cognitive service endpoint
AZURE_OPENAI_SERVICE_KEY = "<AZURE_OPENAI_SERVICE_KEY>"

# Cognitive service endpoint
AZURE_OPENAI_SERVICE_ENDPOINT="<AZURE_OPENAI_SERVICE_ENDPOINT>"

# Cognitive service endpoint
AZURE_OPENAI_DEPLOYMENT_MODEL_NAME="<AZURE_OPENAI_DEPLOYMENT_MODEL_NAME>"

# Callback events URI to handle callback events.
CALLBACK_URI_HOST = "<CALLBACK_URI_HOST_WITH_PROTOCOL>"
CALLBACK_EVENTS_URI = CALLBACK_URI_HOST + "/api/callbacks"

call_automation_client = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)

recording_id = None
recording_chunks_location = []

openai.api_key = AZURE_OPENAI_SERVICE_KEY
openai.api_base = AZURE_OPENAI_SERVICE_ENDPOINT # your endpoint should look like the following https://YOUR_RESOURCE_NAME.openai.azure.com/
openai.api_type = 'azure'
openai.api_version = '2023-05-15' # this may change in the future

app = Flask(__name__)

def get_chat_gpt_response(speech_input):
    # Define your chat completions request
    chat_request = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": f"In less than 200 characters: respond to this question: {speech_input}?"}
    ]
  
    global response_content
    try:
        response = ChatCompletion.create(model=AZURE_OPENAI_DEPLOYMENT_MODEL_NAME,
                                         deployment_id=AZURE_OPENAI_DEPLOYMENT_MODEL_NAME, 
                                         messages=chat_request,
                                         max_tokens = 1000)
    except ex:
        app.logger.info("error in openai api call : %s",ex)
    # Extract the response content
    if response is not None :
         response_content  =  response['choices'][0]['message']['content']
    else :
         response_content="" 
    app.logger.info("response from open ai: %s", response_content)
    return response_content

def handle_recognize(replyText,callerId,call_connection_id,context=""):
    play_source = TextSource(text=replyText, voice_name="en-US-NancyNeural")    
    recognize_result=call_automation_client.get_call_connection(call_connection_id).start_recognizing_media( 
    input_type=RecognizeInputType.SPEECH,
    target_participant=PhoneNumberIdentifier(callerId), 
    end_silence_timeout=10, 
    play_prompt=play_source,
    operation_context=context)

def handle_play(call_connection_id):     
    play_source = TextSource(text="Goodbye", voice_name= "en-US-NancyNeural") 
    call_automation_client.get_call_connection(call_connection_id).play_media_to_all(play_source,
                                                                                     operation_context="GoodBye")
    
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
                 handle_recognize("Hello. How can I help?",
                                  caller_id,call_connection_id,
                                  context="GetFreeFormText") 
                 
            elif event.type == "Microsoft.Communication.RecognizeCompleted":
                 if event.data['recognitionType'] == "speech": 
                     speech_text = event.data['speechResult']['speech']; 
                     app.logger.info("Recognition completed, speech_text =%s", 
                                     speech_text); 
                     if speech_text is not None and len(speech_text) > 0: 
                        chat_gpt_response= get_chat_gpt_response(speech_text)
                        handle_recognize(replyText=chat_gpt_response,
                                         callerId=caller_id,
                                         call_connection_id=call_connection_id,
                                         context="OpenAISample")

            elif event.type == "Microsoft.Communication.RecognizeFailed": 
                 resultInformation = event.data['resultInformation']
                 reasonCode = resultInformation['subCode']
                 context=event.data['operationContext']
                 retryContext = "retry"
                 if context == retryContext:
                    handle_play(call_connection_id=call_connection_id)

                 else:
                    if reasonCode in {8510}:
                        replyText =  "I've noticed that you have been silent. Are you still there?"
                        handle_recognize(replyText=replyText,
                                  callerId=caller_id,
                                  call_connection_id=call_connection_id,
                                  context=retryContext)
                    else: 
                        handle_play(call_connection_id=call_connection_id)
                 
            elif event.type == "Microsoft.Communication.PlayCompleted" or event.type == "Microsoft.Communication.playFailed":
                app.logger.info("Received PlayCompleted event")
                handle_hangup(call_connection_id)
	
        return Response(status=200) 
    except Exception as ex:
        app.logger.info("error in event handling")

@app.route("/")
def hello():
    return "Hello ACS CallAutomation!..test"

if __name__ == '__main__':
    app.logger.setLevel(INFO)
    app.run(port=8080)
