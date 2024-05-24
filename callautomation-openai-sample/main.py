
from pyexpat import model
import uuid
from urllib.parse import urlencode, urljoin
from azure.eventgrid import EventGridEvent, SystemEventNames
import requests
from flask import Flask, Response, request, json
import functools
from logging import INFO
import re
from aiohttp import web
from azure.communication.callautomation import (
    PhoneNumberIdentifier,
    RecognizeInputType,
    TextSource
    )
from azure.communication.callautomation.aio import (
    CallAutomationClient
    )
from azure.core.messaging import CloudEvent
import asyncio
from openai  import AsyncAzureOpenAI

# Your ACS resource connection string
ACS_CONNECTION_STRING = ""

# Cognitive service endpoint
COGNITIVE_SERVICE_ENDPOINT=""

# Cognitive service endpoint
AZURE_OPENAI_SERVICE_KEY = ""

# Open AI service endpoint
AZURE_OPENAI_SERVICE_ENDPOINT=""

# Azure Open AI Deployment Model Name
AZURE_OPENAI_DEPLOYMENT_MODEL_NAME="call-automation-deployment"

# Azure Open AI Deployment Model
AZURE_OPENAI_DEPLOYMENT_MODEL="gpt-3.5-turbo"

# Agent Phone Number
AGENT_PHONE_NUMBER=""

# Callback events URI to handle callback events.
CALLBACK_URI_HOST = ""
CALLBACK_EVENTS_URI = CALLBACK_URI_HOST + "/api/callbacks"

ANSWER_PROMPT_SYSTEM_TEMPLATE = """ 
    You are an assistant designed to answer the customer query and analyze the sentiment score from the customer tone. 
    You also need to determine the intent of the customer query and classify it into categories such as sales, marketing, shopping, etc.
    Use a scale of 1-10 (10 being highest) to rate the sentiment score. 
    Use the below format, replacing the text in brackets with the result. Do not include the brackets in the output: 
    Content:[Answer the customer query briefly and clearly in two lines and ask if there is anything else you can help with] 
    Score:[Sentiment score of the customer tone] 
    Intent:[Determine the intent of the customer query] 
    Category:[Classify the intent into one of the categories]
    """

HELLO_PROMPT = "Hello, thank you for calling! How can I help you today?"
TIMEOUT_SILENCE_PROMPT = "I am sorry, I did not hear anything. If you need assistance, please let me know how I can help you,"
GOODBYE_PROMPT = "Thank you for calling! I hope I was able to assist you. Have a great day!"
CONNECT_AGENT_PROMPT = "I'm sorry, I was not able to assist you with your request. Let me transfer you to an agent who can help you further. Please hold the line, and I willl connect you shortly."
CALLTRANSFER_FAILURE_PROMPT = "It looks like I can not connect you to an agent right now, but we will get the next available agent to call you back as soon as possible."
AGENT_PHONE_NUMBER_EMPTY_PROMPT = "I am sorry, we are currently experiencing high call volumes and all of our agents are currently busy. Our next available agent will call you back as soon as possible."
END_CALL_PHRASE_TO_CONNECT_AGENT = "Sure, please stay on the line. I am going to transfer you to an agent."

TRANSFER_FAILED_CONTEXT = "TransferFailed"
CONNECT_AGENT_CONTEXT = "ConnectAgent"
GOODBYE_CONTEXT = "Goodbye"

CHAT_RESPONSE_EXTRACT_PATTERN = r"\s*Content:(.*)\s*Score:(.*\d+)\s*Intent:(.*)\s*Category:(.*)"

call_automation_client = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)

recording_id = None
recording_chunks_location = []
max_retry = 2

app = Flask(__name__)

""" def async_action():
    def wrapper(func):
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
             # Some fancy foo stuff
            return await func(*args, **kwargs)
        return wrapped
    return wrapper """

def async_action(f):
    @functools.wraps(f)
    async def wrapped(*args, **kwargs):
        return await f(*args, **kwargs)
    return wrapped

openai_client = AsyncAzureOpenAI(
    # This is the default and can be omitted
    api_key=AZURE_OPENAI_SERVICE_KEY,
    api_version="2024-02-01",
    azure_endpoint=AZURE_OPENAI_SERVICE_ENDPOINT
)


async def get_chat_completions_async(system_prompt,user_prompt): 
    """     openai.api_key = AZURE_OPENAI_SERVICE_KEY
    openai.api_base = AZURE_OPENAI_SERVICE_ENDPOINT # your endpoint should look like the following https://YOUR_RESOURCE_NAME.openai.azure.com/
    openai.api_type = 'azure'
    openai.api_version = '2023-05-15' # this may change in the future """
    
    # Define your chat completions request
    chat_request = [
        {"role": "system", "content": f"{system_prompt}"},
        {"role": "user", "content": f"In less than 200 characters: respond to this question: {user_prompt}?"}
    ]
  
    app.logger.info("get_chat_completions_async")

    
    """  models = openai_client.models
    for model in models:
        app.logger.info(model) """
    global response_content
    global response
    try:
        response = await openai_client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_MODEL_NAME,
            messages=chat_request,
            max_tokens = 1000)
    except Exception as ex:
        app.logger.info("error in openai api call : %s", ex)

    # Extract the response content
    if response is not None :
         response_content  =  response.choices[0].message.content
    else :
         response_content = ""
    
    app.logger.info("chat gpt resonse content : %s", response_content)
    return response_content


async def get_chat_gpt_response(speech_input):
    app.logger.info("get_chat_gpt_response, speech_text =%s", 
                                     speech_input)
    return await get_chat_completions_async(ANSWER_PROMPT_SYSTEM_TEMPLATE,speech_input)


async def handle_recognize(replyText,callerId,call_connection_id,context=""):
    play_source = TextSource(text=replyText, voice_name="en-US-NancyNeural")    
    recognize_result= await call_automation_client.get_call_connection(call_connection_id).start_recognizing_media( 
    input_type=RecognizeInputType.SPEECH,
    target_participant=PhoneNumberIdentifier(callerId), 
    end_silence_timeout=10, 
    play_prompt=play_source,
    operation_context=context)
    app.logger.info("handle_recognize : data=%s",recognize_result) 


async def handle_play(call_connection_id, text_to_play, context):     
    play_source = TextSource(text=text_to_play, voice_name= "en-US-NancyNeural") 
    await call_automation_client.get_call_connection(call_connection_id).play_media_to_all(play_source,
                                                                                     operation_context=context)


async def handle_hangup(call_connection_id):     
    await call_automation_client.get_call_connection(call_connection_id).hang_up(is_for_everyone=True)


async def detect_escalate_to_agent_intent(speech_text, logger):
    return await has_intent_async(user_query=speech_text, intent_description="talk to agent", logger=logger)


async def has_intent_async(user_query, intent_description, logger):
    is_match=False
    system_prompt = "You are a helpful assistant"
    combined_prompt = f"In 1 word: does {user_query} have a similar meaning as {intent_description}?"

    logger.info("has_intent_async method executing")

    #combined_prompt = base_user_prompt.format(user_query, intent_description)
    response = await get_chat_completions_async(system_prompt, combined_prompt)
    if "yes" in response.lower():
        is_match =True        
    logger.info(f"OpenAI results: is_match={is_match}, customer_query='{user_query}', intent_description='{intent_description}'")
    return is_match

def get_sentiment_score(sentiment_score):
    pattern = r"(\d)+"
    regex = re.compile(pattern)
    match = regex.search(sentiment_score)
    return int(match.group()) if match else -1

@app.route("/api/incomingCall",  methods=['POST'])
#@async_action
async def incoming_call_handler():
    #data = await request.get_json()
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

                answer_call_result = await call_automation_client.answer_call(incoming_call_context=incoming_call_context,
                                                                        cognitive_services_endpoint=COGNITIVE_SERVICE_ENDPOINT,
                                                                        callback_url=callback_uri)
                app.logger.info("Answered call for connection id: %s",
                                answer_call_result.call_connection_id)
                return Response(status=200)
            
@app.route("/api/callbacks/<contextId>", methods=["POST"])
#@async_action
async def handle_callback(contextId):    
    try:        
        global caller_id , call_connection_id
        #request_json = await request.get_json()
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
                await handle_recognize(HELLO_PROMPT,
                                  caller_id,call_connection_id,
                                  context="GetFreeFormText") 
                 
            elif event.type == "Microsoft.Communication.RecognizeCompleted":
                 if event.data['recognitionType'] == "speech": 
                     speech_text = event.data['speechResult']['speech']; 
                     app.logger.info("Recognition completed, speech_text =%s", 
                                     speech_text); 
                     if speech_text is not None and len(speech_text) > 0: 
                        """  if await detect_escalate_to_agent_intent(speech_text=speech_text,logger=app.logger):
                            handle_play(call_connection_id=call_connection_id,text_to_play=END_CALL_PHRASE_TO_CONNECT_AGENT,context=CONNECT_AGENT_CONTEXT)    
                        else:  """
                        app.logger.info("sending text to opanai, speech_text =%s", 
                                    speech_text); 
                        chat_gpt_response= await get_chat_gpt_response(speech_text)
                        app.logger.info(f"Chat GPT response:{chat_gpt_response}") 
                        regex = re.compile(CHAT_RESPONSE_EXTRACT_PATTERN)
                        match = regex.search(chat_gpt_response)
                        if match:
                            answer = match.group(1)
                            sentiment_score = match.group(2).strip()
                            intent = match.group(3)
                            category = match.group(4)
                            app.logger.info(f"Chat GPT Answer={answer}, Sentiment Rating={sentiment_score}, Intent={intent}, Category={category}") 
                            score=get_sentiment_score(sentiment_score)
                            app.logger.info(f"Score={score}")
                            if -1 < score < 5:
                                app.logger.info(f"Score is less than 5")
                                await handle_play(call_connection_id=call_connection_id,text_to_play=CONNECT_AGENT_PROMPT,context=CONNECT_AGENT_CONTEXT)
                            else:
                                app.logger.info(f"Score is more than 5")
                                await handle_recognize(answer,caller_id,call_connection_id,context="OpenAISample")
                        else: 
                            app.logger.info("No match found")
                            await handle_recognize(chat_gpt_response,caller_id,call_connection_id,context="OpenAISample")

            elif event.type == "Microsoft.Communication.RecognizeFailed":
                resultInformation = event.data['resultInformation']
                reasonCode = resultInformation['subCode']
                context=event.data['operationContext']
                global max_retry
                if reasonCode == 8510 and 0 < max_retry:
                    await handle_recognize(TIMEOUT_SILENCE_PROMPT,caller_id,call_connection_id) 
                    max_retry -= 1
                else:
                    await handle_play(call_connection_id,GOODBYE_PROMPT, GOODBYE_CONTEXT)    
                 
            elif event.type == "Microsoft.Communication.PlayCompleted":
                context=event.data['operationContext'] 
                app.logger.info(f"Context: " + context)
                if context.lower() == TRANSFER_FAILED_CONTEXT.lower() or context.lower() == GOODBYE_CONTEXT.lower() :
                    await handle_hangup(call_connection_id)
                elif context.lower() ==  CONNECT_AGENT_CONTEXT.lower():
                    if not AGENT_PHONE_NUMBER or AGENT_PHONE_NUMBER.isspace():
                        app.logger.info(f"Agent phone number is empty")
                        await handle_play(call_connection_id=call_connection_id,text_to_play=AGENT_PHONE_NUMBER_EMPTY_PROMPT)  
                    else:
                        app.logger.info(f"Initializing the Call transfer...")
                        transfer_destination=PhoneNumberIdentifier(AGENT_PHONE_NUMBER)                       
                        await call_automation_client.get_call_connection(call_connection_id=call_connection_id).transfer_call_to_participant(target_participant=transfer_destination)
                        app.logger.info(f"Transfer call initiated: {context}")
	
            elif event.type == "Microsoft.Communication.CallTransferAccepted":
                app.logger.info(f"Call transfer accepted event received for connection id: {call_connection_id}")   
             
            elif event.type == "Microsoft.Communication.CallTransferFailed":
                app.logger.info(f"Call transfer failed event received for connection id: {call_connection_id}")
                resultInformation = event.data['resultInformation']
                sub_code = resultInformation['subCode']
                # check for message extraction and code
                app.logger.info(f"Encountered error during call transfer, message=, code=, subCode={sub_code}")                
                await handle_play(call_connection_id=call_connection_id,text_to_play=CALLTRANSFER_FAILURE_PROMPT, context=TRANSFER_FAILED_CONTEXT)
        return Response(status=200) 
    except ex:
        app.logger.info(f"error in event handling exception = {ex}")

@app.route("/")
def hello():
    return "Hello ACS CallAutomation!..test"

async def init_app():
   """Initialize the aiohttp web application."""
   app = web.Application()
   app.router.add_post('/api/incomingCall', incoming_call_handler)
   app.router.add_post('/api/callbacks/<contextId>', handle_callback)
   return app

if __name__ == '__main__':
    app.logger.setLevel(INFO)
    app.run(port=8080)
    
    #loop = asyncio.get_event_loop()
    #web.run_app(init_app(), host='0.0.0.0', port=5000, loop=loop)
    #asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
