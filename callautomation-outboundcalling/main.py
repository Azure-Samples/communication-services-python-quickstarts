from azure.eventgrid import EventGridEvent, SystemEventNames
from flask import Flask, Response, request, json, send_file, render_template, redirect
from logging import INFO
import time
from azure.communication.callautomation import (
    CallAutomationClient,
    CommunicationUserIdentifier,
    CallConnectionClient,
    PhoneNumberIdentifier,
    RecognizeInputType,
    MicrosoftTeamsUserIdentifier,
    CallInvite,
    RecognitionChoice,
    DtmfTone,
    TextSource,
    RoomCallLocator,
    GroupCallLocator,
    ServerCallLocator)
from azure.core.messaging import CloudEvent

# Your ACS resource connection string
ACS_CONNECTION_STRING = ""

# Your ACS resource phone number will act as source number to start outbound call
ACS_PHONE_NUMBER = ""

# Target phone number you want to receive the call.
TARGET_PHONE_NUMBER = ""

# Callback events URI to handle callback events.
CALLBACK_URI_HOST = ""
CALLBACK_EVENTS_URI = CALLBACK_URI_HOST + "/api/callbacks"
COGNITIVE_SERVICES_ENDPOINT = ""

#(OPTIONAL) Your target Microsoft Teams user Id ex. "ab01bc12-d457-4995-a27b-c405ecfe4870"
TARGET_TEAMS_USER_ID = "<TARGET_TEAMS_USER_ID>"

TEMPLATE_FILES_PATH = "template"

# Prompts for text to speech
SPEECH_TO_TEXT_VOICE = "en-US-NancyNeural"
MAIN_MENU = "Hello this is Contoso Bank, we’re calling in regard to your appointment tomorrow at 9am to open a new account. Please say confirm if this time is still suitable for you or say cancel if you would like to cancel this appointment."
CONFIRMED_TEXT = "Thank you for confirming your appointment tomorrow at 9am, we look forward to meeting with you."
CANCEL_TEXT = "Your appointment tomorrow at 9am has been cancelled. Please call the bank directly if you would like to rebook for another date and time."
CUSTOMER_QUERY_TIMEOUT = "I’m sorry I didn’t receive a response, please try again."
NO_RESPONSE = "I didn't receive an input, we will go ahead and confirm your appointment. Goodbye"
INVALID_AUDIO = "I’m sorry, I didn’t understand your response, please try again."
CONFIRM_CHOICE_LABEL = "Confirm"
CANCEL_CHOICE_LABEL = "Cancel"
RETRY_CONTEXT = "retry"
is_connect_api_called = False
call_automation_client = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)

app = Flask(__name__,
            template_folder=TEMPLATE_FILES_PATH)

def get_choices():
    choices = [
                RecognitionChoice(label = CONFIRM_CHOICE_LABEL, phrases= ["Confirm", "First", "One"], tone = DtmfTone.ONE),
                RecognitionChoice(label = CANCEL_CHOICE_LABEL, phrases= ["Cancel", "Second", "Two"], tone = DtmfTone.TWO)
            ]
    return choices

def get_media_recognize_choice_options(call_connection_client: CallConnectionClient, text_to_play: str, target_participant:str, choices: any, context: str):
     play_source =  TextSource (text= text_to_play, voice_name= SPEECH_TO_TEXT_VOICE)
     call_connection_client.start_recognizing_media(
                input_type=RecognizeInputType.CHOICES,
                target_participant=target_participant,
                choices=choices,
                play_prompt=play_source,
                interrupt_prompt=False,
                initial_silence_timeout=10,
                operation_context=context
            )
     
def handle_play(call_connection_client: CallConnectionClient, text_to_play: str):
        play_source = TextSource(text=text_to_play, voice_name=SPEECH_TO_TEXT_VOICE) 
        call_connection_client.play_media_to_all(play_source)

def connect_call():
    global is_connect_api_called
    is_connect_api_called = True
    # call_automation_client.connect_call(
    #     room_id="9943043419816556",
    #     callback_url=CALLBACK_EVENTS_URI,
    #     cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT,
    #     operation_context="connectCallContext")
    
    call_automation_client.connect_call(
        group_call_id="85f7a918-901b-4fcb-9fd9-121d44a003a1",
        callback_url=CALLBACK_EVENTS_URI,
        cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT,
        operation_context="connectCallContext")
    
    # call_automation_client.connect_call(
    #     server_call_id="aHR0cHM6Ly9hcGkuZmxpZ2h0cHJveHkuc2t5cGUuY29tL2FwaS92Mi9jcC9jb252LW1hc28tMDItcHJvZC1ha3MuY29udi5za3lwZS5jb20vY29udi8ydkd2aGdKMEZVZXRoaFNLUkp3bVpRP2k9MTAtMTI4LTg4LTE1MyZlPTYzODUzMTI2OTk2NTA5ODI3Ng",
    #     callback_url=CALLBACK_EVENTS_URI,
    #     cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT,
    #     operation_context="connectCallContext")
    
# GET endpoint to place phone call
@app.route('/outboundCall')
def outbound_call_handler():
    target_participant = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
    source_caller = PhoneNumberIdentifier(ACS_PHONE_NUMBER)
    call_connection_properties = call_automation_client.create_call(target_participant, 
                                                                    CALLBACK_EVENTS_URI,
                                                                    cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT,
                                                                    source_caller_id_number=source_caller)
    app.logger.info("Created call with connection id: %s", call_connection_properties.call_connection_id)
    return redirect("/")


# POST endpoint to handle callback events
@app.route('/api/callbacks', methods=['POST'])
def callback_events_handler():
    global is_connect_api_called
    for event_dict in request.json:
        # Parsing callback events
        event = CloudEvent.from_dict(event_dict)
        call_connection_id = event.data['callConnectionId']
        app.logger.info("%s event received for call connection id: %s", event.type, call_connection_id)
        call_connection_client = call_automation_client.get_call_connection(call_connection_id)
        target_participant = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
        if event.type == "Microsoft.Communication.CallConnected":
            # (Optional) Add a Microsoft Teams user to the call.  Uncomment the below snippet to enable Teams Interop scenario.
            # call_connection_client.add_participant(target_participant = CallInvite(
            #     target = MicrosoftTeamsUserIdentifier(user_id=TARGET_TEAMS_USER_ID),
            #     source_display_name = "Jack (Contoso Tech Support)"))
            
            # app.logger.info("Starting recognize")
            # get_media_recognize_choice_options(
            #     call_connection_client=call_connection_client,
            #     text_to_play=MAIN_MENU, 
            #     target_participant=target_participant,
            #     choices=get_choices(),context="")
            
            if is_connect_api_called == False:
                app.logger.info("Connect Api Initiated....")
                connect_call()
            if event.data.get('operationContext') =="connectCallContext":
                app.logger.info("Connect Api connected...")
                app.logger.info("#####CORRELATION ID:--> %s", event.data["correlationId"])
                app.logger.info("#####CALL CONNECTION ID:--> %s", event.data["callConnectionId"])
                
                call_connection_client.add_participant(target_participant=PhoneNumberIdentifier(TARGET_PHONE_NUMBER),
                                                             source_caller_id_number=PhoneNumberIdentifier(ACS_PHONE_NUMBER),
                                                             operation_context="addPstnUserContext",
                                                             invitation_timeout=10)
                
                # call_connection_client.add_participant(
                #     target_participant=CommunicationUserIdentifier("8:acs:19ae37ff-1a44-4e19-aade-198eedddbdf2_00000020-8828-0f62-0d8b-084822000147"),
                #      operation_context="addVoipUserContext",
                #      invitation_timeout=10)
                
                participants = call_connection_client.list_participants()
                app.logger.info("*****Listing participants in call*****")
                for page in participants.by_page():
                    for participant in page:
                        app.logger.info("Participant: %s", participant.identifier.raw_id)
        elif event.type == "Microsoft.Communication.ConnectFailed": 
                resultInformation = event.data['resultInformation']
                app.logger.info("Encountered error during connect, message=%s, code=%s, subCode=%s", 
                                resultInformation['message'], 
                                resultInformation['code'],
                                resultInformation['subCode'])          
        elif event.type == "Microsoft.Communication.AddParticipantSucceeded":
                app.logger.info(f"Received AddParticipantSucceeded event for connection id: {event.data["callConnectionId"]}")
                participants = call_connection_client.list_participants()
                app.logger.info("&&&&&&&&&&Listing participants in call&&&&&&&&...")
                for page in participants.by_page():
                    for participant in page:
                        app.logger.info("Participant: %s", participant.identifier.raw_id)
                        
                # mute_result = call_connection_client.mute_participant(CommunicationUserIdentifier("8:acs:19ae37ff-1a44-4e19-aade-198eedddbdf2_00000020-8841-537b-e3c7-593a0d0014e2"))
                # if mute_result:
                #     app.logger.info("Participant is muted. wating for confirming.....")
                #     time.sleep(5)
                #     response = call_connection_client.get_participant(CommunicationUserIdentifier("8:acs:19ae37ff-1a44-4e19-aade-198eedddbdf2_00000020-8841-537b-e3c7-593a0d0014e2"))
                #     if response:
                #         app.logger.info(f"Is participant muted: {response.is_muted}")
                #         app.logger.info("Mute participant test completed.") 

                # call_connection_client.remove_participant(target_participant=PhoneNumberIdentifier(TARGET_PHONE_NUMBER))
                
                # call_connection_client.remove_participant(target_participant=CommunicationUserIdentifier("8:acs:19ae37ff-1a44-4e19-aade-198eedddbdf2_00000020-8828-0f62-0d8b-084822000147"))
                # call_connection_client.hang_up(is_for_everyone=False)
                # handle_play(call_connection_client=call_connection_client, text_to_play=CONFIRMED_TEXT)
                
                app.logger.info("Starting recognize")
                get_media_recognize_choice_options(
                call_connection_client=call_connection_client,
                text_to_play=MAIN_MENU, 
                target_participant=target_participant,
                choices=get_choices(),context="")

                
        # Perform different actions based on DTMF tone received from RecognizeCompleted event
        elif event.type == "Microsoft.Communication.RecognizeCompleted":
            app.logger.info("Recognize completed: data=%s", event.data) 
            if event.data['recognitionType'] == "choices": 
                 label_detected = event.data['choiceResult']['label']; 
                 phraseDetected = event.data['choiceResult']['recognizedPhrase']; 
                 app.logger.info("Recognition completed, labelDetected=%s, phraseDetected=%s, context=%s", label_detected, phraseDetected, event.data.get('operationContext'))
                 if label_detected == CONFIRM_CHOICE_LABEL:
                    text_to_play = CONFIRMED_TEXT
                 else:
                    text_to_play = CANCEL_TEXT
                 handle_play(call_connection_client=call_connection_client, text_to_play=text_to_play)

        elif event.type == "Microsoft.Communication.RecognizeFailed":
            failedContext = event.data['operationContext']
            if(failedContext and failedContext == RETRY_CONTEXT):
                handle_play(call_connection_client=call_connection_client, text_to_play=NO_RESPONSE)
            else:
                resultInformation = event.data['resultInformation']
                app.logger.info("Encountered error during recognize, message=%s, code=%s, subCode=%s", 
                                resultInformation['message'], 
                                resultInformation['code'],
                                resultInformation['subCode'])
                if(resultInformation['subCode'] in[8510, 8510]):
                    textToPlay =CUSTOMER_QUERY_TIMEOUT
                else :
                    textToPlay =INVALID_AUDIO
                
                get_media_recognize_choice_options(
                    call_connection_client=call_connection_client,
                    text_to_play=textToPlay, 
                    target_participant=target_participant,
                    choices=get_choices(),context=RETRY_CONTEXT)

        elif event.type in ["Microsoft.Communication.PlayCompleted", "Microsoft.Communication.PlayFailed"]:
            app.logger.info("Terminating call")
            call_connection_client.hang_up(is_for_everyone=True)

        return Response(status=200)

# GET endpoint to render the menus
@app.route('/')
def index_handler():
    return render_template("index.html")


if __name__ == '__main__':
    app.logger.setLevel(INFO)
    app.run(port=5001)
