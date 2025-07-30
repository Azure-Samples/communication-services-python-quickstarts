import os
import logging
import json
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin
from fastapi import FastAPI, HTTPException, status, Body
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from azure.eventgrid import EventGridEvent, SystemEventNames
from azure.core.messaging import CloudEvent
from azure.communication.callautomation.aio import CallAutomationClient
from azure.communication.callautomation import (
    PhoneNumberIdentifier,
    CommunicationUserIdentifier
)
from fastapi.responses import Response

# ACS Connection String and other configurations; TO BE UPDATED BEFORE RUNNING THE APP
# For local development, you can use environment variables or a .env file.
ACS_CONNECTION_STRING=""
CALLBACK_URI_HOST=""
PMA_ENDPOINT=""
ACS_OUTBOUND_PHONE_NUMBER=""
ACS_INBOUND_PHONE_NUMBER=""
ACS_USER_PHONE_NUMBER=""
ACS_TEST_IDENTITY2=""
ACS_TEST_IDENTITY3=""

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bootstrap - FastAPI application setup
app = FastAPI(
    title="Move Participants Sample",
    description="Azure Communication Services Call Automation Move Participants Sample",
    version="1.0.0"
)

# Global Variables for Move Participants Scenario
acs_connection_string: str = ACS_CONNECTION_STRING
callback_uri_host: str = CALLBACK_URI_HOST

# Phone numbers and identities for Move Participants scenario
acs_outbound_phone_number: str = ACS_OUTBOUND_PHONE_NUMBER
acs_inbound_phone_number: str = ACS_INBOUND_PHONE_NUMBER
acs_user_phone_number: str = ACS_USER_PHONE_NUMBER
acs_test_identity2: str = ACS_TEST_IDENTITY2
acs_test_identity3: str = ACS_TEST_IDENTITY3

# Track which type of workflow call was last created
last_workflow_call_type: str = ""  # "CallTwo" or "CallThree"

# Call connection IDs
call_connection_id: str = ""
call_connection_id1: str = ""  # User's incoming call
call_connection_id2: str = ""  # ACS user's redirected call

# Initialize client as None initially
client: Optional[CallAutomationClient] = None

def get_config_value(key: str, default: str = "") -> str:
    """Get configuration value from environment variables or use default"""
    value = os.getenv(key, default)
    if not value and not default:
        raise ValueError(f"Configuration value '{key}' is required but not provided")
    return value

def initialize_client():
    """Initialize the CallAutomationClient with current configuration"""
    global client
    if acs_connection_string:
        client = CallAutomationClient.from_connection_string(acs_connection_string)

# Initialize configuration from environment variables
try:
    # acs_connection_string = get_config_value("ACS_CONNECTION_STRING")
    # callback_uri_host = get_config_value("CALLBACK_URI_HOST")
    # acs_outbound_phone_number = get_config_value("ACS_OUTBOUND_PHONE_NUMBER")
    # acs_inbound_phone_number = get_config_value("ACS_INBOUND_PHONE_NUMBER")
    # acs_user_phone_number = get_config_value("ACS_USER_PHONE_NUMBER")
    # acs_test_identity2 = get_config_value("ACS_TEST_IDENTITY2")
    # acs_test_identity3 = get_config_value("ACS_TEST_IDENTITY3")
    #     
    initialize_client()
    logger.info("Configuration loaded from environment variables")
except ValueError as e:
    logger.warning(f"Configuration not fully loaded from environment: {e}")
    logger.info("Configuration can be set via /setConfigurations endpoint")

# Pydantic models
class ConfigurationRequest(BaseModel):
    acs_connection_string: Optional[str] = None
    callback_uri_host: Optional[str] = None
    acs_outbound_phone_number: Optional[str] = None
    acs_inbound_phone_number: Optional[str] = None
    acs_user_phone_number: Optional[str] = None
    acs_test_identity2: Optional[str] = None
    acs_test_identity3: Optional[str] = None

class MoveParticipantsRequest(BaseModel):
    participant_to_move: str
    source_call_connection_id: str
    target_call_connection_id: str

# Configuration Endpoint
@app.post("/setConfigurations", tags=["Configuration"])
async def set_configurations(configuration_request: ConfigurationRequest):
    """Set configuration values for the application"""
    global acs_connection_string, callback_uri_host
    global acs_outbound_phone_number, acs_inbound_phone_number, acs_user_phone_number
    global acs_test_identity2, acs_test_identity3
    
    try:
        if configuration_request.acs_connection_string:
            acs_connection_string = configuration_request.acs_connection_string
        if configuration_request.callback_uri_host:
            callback_uri_host = configuration_request.callback_uri_host
        if configuration_request.acs_outbound_phone_number:
            acs_outbound_phone_number = configuration_request.acs_outbound_phone_number
        if configuration_request.acs_inbound_phone_number:
            acs_inbound_phone_number = configuration_request.acs_inbound_phone_number
        if configuration_request.acs_user_phone_number:
            acs_user_phone_number = configuration_request.acs_user_phone_number
        if configuration_request.acs_test_identity2:
            acs_test_identity2 = configuration_request.acs_test_identity2
        if configuration_request.acs_test_identity3:
            acs_test_identity3 = configuration_request.acs_test_identity3

        # Reinitialize client with new configuration
        initialize_client()
        
        log_msg = "Configuration is set successfully.\nInitialized call automation client."
        print(log_msg)
        return {"message": log_msg}
        
    except Exception as e:
        logger.error(f"Error setting configuration: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/MoveParticipantEvent")
async def move_participant_event(events: List[Dict[str, Any]] = Body(...)):
    """Handle Event Grid events for move participants scenario"""
    global call_connection_id1, last_workflow_call_type, client
    
    if not client:
        raise HTTPException(status_code=500, detail="CallAutomationClient not initialized")

    msg_log = ["\n~~~~~~~~~~~~ /api/MoveParticipantEvent (Event Grid Hook) ~~~~~~~~~~~~"]
    print("\n~~~~~~~~~~~~ /api/MoveParticipantEvent (Event Grid Hook) ~~~~~~~~~~~~")
    try:
        for event_data in events:
            event = EventGridEvent.from_dict(event_data)
            print(f"Event received: {event.event_type}")    
            
            if event.event_type == SystemEventNames.EventGridSubscriptionValidationEventName:
                validation_data = event.data
                validation_code = validation_data.get("validationCode", "")
                return Response(content=json.dumps({"validationResponse": validation_code}),status_code=200, media_type="application/json")
            
            elif event.event_type == "Microsoft.Communication.IncomingCall":
                incoming_call_data = event.data
                # msg_log.append(f"Event received: {event.event_type}")
                from_caller_id = event.data['from']["phoneNumber"]["value"] if event.data['from']['kind'] =="phoneNumber" else event.data['from']['rawId']
                to_caller_id = event.data['to']["phoneNumber"]["value"] if event.data['to']['kind'] =="phoneNumber" else event.data['to']['rawId']

                print(f'from_caller_id: {from_caller_id}, \nto_caller_id: {to_caller_id}, \nacs_user_phone_number: {acs_user_phone_number}')

                # Call 1: User calls from their phone number to ACS inbound number
                if acs_user_phone_number in from_caller_id:
                    callback_uri = urljoin(callback_uri_host, "/api/callbacks")
                    
                    answer_call_result = await client.answer_call(
                        incoming_call_context=incoming_call_data.get("incomingCallContext"),
                        callback_url=callback_uri,
                        operation_context="IncomingCallFromUser"
                    )
                    print('Call 1 Answered: User called from their phone number to ACS inbound number')
                    call_connection_id1 = answer_call_result.call_connection_id
                    
                    msg_log.extend([
                        "User Call Answered by Call Automation.",
                        f"From Caller Raw Id: {from_caller_id}",
                        f"To Caller Raw Id:   {to_caller_id}",
                        f"Internal Connection Id: {call_connection_id1}",
                        f"Correlation Id:         {incoming_call_data.get('correlationId', '')}"
                    ])
                
                # Call 2: ACS inbound number calls ACS outbound number (workflow triggered)
                elif acs_inbound_phone_number in from_caller_id:
                    incoming_call_context = incoming_call_data.get("incomingCallContext")
                    
                    # Check which type of workflow call this is and redirect accordingly
                    if last_workflow_call_type == "CallTwo":
                        # Redirect the call to ACS User Identity 2
                        await client.redirect_call(
                            incoming_call_context=incoming_call_context,
                            target_participant=CommunicationUserIdentifier(acs_test_identity2)
                        )

                        msg_log.extend([
                            f"Call2 redirected to ACS User Identity 2: {acs_test_identity2}",
                            f"From Caller Raw Id: {from_caller_id}",
                            f"To Caller Raw Id  : {to_caller_id}"
                        ])
                    
                    elif last_workflow_call_type == "CallThree":
                        # Redirect the call to ACS User Identity 3
                        await client.redirect_call(
                            incoming_call_context=incoming_call_context,
                            target_participant=CommunicationUserIdentifier(acs_test_identity3)
                        )
                        
                        msg_log.extend([
                            f"Call3 redirected to ACS User Identity 3: {acs_test_identity3}",
                            f"From Caller Raw Id: {from_caller_id}",
                            f"To Caller Raw Id  : {to_caller_id}"
                        ])
                    
                    else:
                        logger.warning(f"Unknown workflow call type: {last_workflow_call_type}. Defaulting to Call Two behavior.")
                        
                        # Default to Call Two behavior
                        await client.redirect_call(
                            incoming_call_context=incoming_call_context,
                            target_participant=CommunicationUserIdentifier(acs_test_identity2)
                        )
    
                        msg_log.append(f"Default: Redirected to ACS User Identity 2: {acs_test_identity2}")
        
        log_to_send = "\n".join(msg_log)
        print(log_to_send)
        return Response(content=log_to_send, status_code=200)

    except Exception as e:
        logger.error(f"Error processing move participant event: {e}")
        return Response(content=str(e), status_code=500)

# Main Callback Handler
@app.post("/api/callbacks")
async def callbacks(events: List[Dict[str, Any]] = Body(...)):
    """Handle Call Automation callback events"""
    global client
    
    if not client:
        return Response(status=500, content="CallAutomationClient not initialized")
    
    msg_log = []
    
    try:
        for event_data in events:
            cloud_event = CloudEvent.from_dict(event_data)
            # parsed_event = CallAutomationEventParser.parse(cloud_event)
            call_connection_id = cloud_event.data.get('callConnectionId') or cloud_event.data["callConnectionId"]
            # call_connection = client.get_call_connection(call_connection_id)
            
            operation_context = cloud_event.data.get('operationContext', '')
            print(f"Operation Context: {operation_context}")
            event_type = cloud_event.data.get('type', cloud_event.type)
            
            if operation_context:
                if "CallConnected" in event_type:
                    if operation_context == "CallTwo":
                        msg_log.extend([
                            "~~~~~~~~~~~~  /api/callbacks ~~~~~~~~~~~~",
                            f"Received call event  : CallConnected",
                            f"Call 2 Internal Connection Id: {call_connection_id}",
                            f"Correlation Id:                {cloud_event.data.get('correlationId', '')}"
                        ])
                    elif operation_context == "CallThree":
                        msg_log.extend([
                            "~~~~~~~~~~~~  /api/callbacks ~~~~~~~~~~~~",
                            f"Received call event  : CallConnected",
                            f"Call 3 Internal Connection Id: {call_connection_id}",
                            f"Correlation Id:                {cloud_event.data.get('correlationId', '')}"
                        ])
                
                elif "CallDisconnected" in event_type:
                    msg_log.extend([
                        "~~~~~~~~~~~~  /api/callbacks ~~~~~~~~~~~~",
                        f"Received event: CallDisconnected",
                        f"Call Connection Id: {call_connection_id}",
                        ""
                    ])
        
        if msg_log:
            log_output = "\n".join(msg_log)
            print(log_output)
            return PlainTextResponse(content=log_output)
        else:
            return PlainTextResponse(content="")
            
    except Exception as e:
        logger.error(f"Error processing callback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Move Participants Workflow Endpoints
@app.post("/CreateCall1(UserCallToCallAutomation)", tags=["Move Participants APIs"])
async def create_call1():
    """Create Call 1 - User Call to Call Automation"""
    global call_connection_id, client
    
    if not client:
        raise HTTPException(status_code=500, detail="CallAutomationClient not initialized")
    
    msg_log = [
        "",
        "~~~~~~~~~~~~ /CreateCall1(UserCallToCallAutomation)  ~~~~~~~~~~~~"
    ]
    
    try:
        callback_uri = urljoin(callback_uri_host, "/api/callbacks")
        caller = PhoneNumberIdentifier(acs_user_phone_number)
        # Create the call to the ACS inbound phone number
        create_call_result = await client.create_call(
            target_participant=PhoneNumberIdentifier(acs_inbound_phone_number),
            callback_url=callback_uri,
            source_caller_id_number=caller        
        )

        call_connection_id = create_call_result.call_connection_id

        msg_log.extend([
            "Call 1(External PSTN to Call Automation, then be answered by Call Automation):",
            "------------------------------------------------------------------------------",
            f"From: {acs_user_phone_number}",
            f"To:   {acs_inbound_phone_number}",
            f"Target Call Connection Id: {call_connection_id}",
            f"Correlation Id:            {create_call_result.correlation_id}"
        ])
        
        log_output = "\n".join(msg_log)
        print(log_output)
        return PlainTextResponse(content=log_output)
        
    except Exception as e:
        logger.error(f"Error creating Call 1: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/CreateCall2(ToPstnUserFirstAndRedirectToAcsIentity)", tags=["Move Participants APIs"])
async def create_call2():
    """Create Call 2 - To PSTN User First And Redirect To ACS Identity"""
    global call_connection_id1, last_workflow_call_type, client
    
    if not client:
        raise HTTPException(status_code=500, detail="CallAutomationClient not initialized")
    
    msg_log = [
        "",
        "~~~~~~~~~~~~ /CreateCall2(ToPstnUserFirstAndRedirectToAcsIentity) ~~~~~~~~~~~~"
    ]
    
    try:
        callback_uri = urljoin(callback_uri_host, "/api/callbacks")
        caller = PhoneNumberIdentifier(acs_inbound_phone_number)
        create_call_result = await client.create_call(
            target_participant=PhoneNumberIdentifier(acs_outbound_phone_number),
            callback_url=callback_uri,
            source_caller_id_number=caller,
            operation_context="CallTwo"
        )
        last_workflow_call_type = "CallTwo"  # Track this as Call 2
        call_connection_id1 = create_call_result.call_connection_id

        msg_log.extend([
            "Call 2:",
            "-------",
            f"From: {acs_inbound_phone_number}",
            f"To:   {acs_outbound_phone_number}",
            f"Source Call Connection Id: {call_connection_id1}",
            f"Correlation Id:            {create_call_result.correlation_id}",
            f"Redirect Call2 to: {acs_test_identity2}"
        ])
        
        log_output = "\n".join(msg_log)
        print(log_output)
        return PlainTextResponse(content=log_output)
        
    except Exception as e:
        logger.error(f"Error creating Call 2: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/CreateCall3(ToPstnUserFirstAndRedirectToAcsIentity)", tags=["Move Participants APIs"])
async def create_call3():
    """Create Call 3 - To PSTN User First And Redirect To ACS Identity"""
    global call_connection_id2, last_workflow_call_type, client
    
    if not client:
        raise HTTPException(status_code=500, detail="CallAutomationClient not initialized")
    
    msg_log = [
        "",
        "~~~~~~~~~~~~ /CreateCall3(ToPstnUserFirstAndRedirectToAcsIentity)  ~~~~~~~~~~~~"
    ]
    
    try:
        callback_uri = urljoin(callback_uri_host, "/api/callbacks")
        caller = PhoneNumberIdentifier(acs_inbound_phone_number)

        # call_invite = CallInvite(
        #     target=PhoneNumberIdentifier(acs_outbound_phone_number),
        #     source_caller_id_number=caller
        # )
        # create_call_options = CreateCallOptions(
        #     target_participant=call_invite.target,
        #     callback_url=callback_uri,
        #     source_caller_id_number=caller
        # )
        # create_call_options.operation_context = "CallThree"
        
        # create_call_result = await client.create_call(create_call_options)

        create_call_result = await client.create_call(
            target_participant=PhoneNumberIdentifier(acs_outbound_phone_number),
            callback_url=callback_uri,
            source_caller_id_number=caller,
            operation_context="CallThree"
        )

        last_workflow_call_type = "CallThree"  # Track this as Call 3
        call_connection_id2 = create_call_result.call_connection_id

        msg_log.extend([
            "Call 3:",
            "-------",
            f"From: {acs_inbound_phone_number}",
            f"To:   {acs_outbound_phone_number}",
            f"Source Call Connection Id: {call_connection_id2}",
            f"Correlation Id:            {create_call_result.correlation_id}",
            f"Redirect Call3 to: {acs_test_identity3}"
        ])
        
        log_output = "\n".join(msg_log)
        print(log_output)
        return PlainTextResponse(content=log_output)
        
    except Exception as e:
        logger.error(f"Error creating Call 3: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/MoveParticipant", tags=["Move Participants APIs"])
async def move_participant(request: MoveParticipantsRequest):
    """Move participants between calls"""
    global client
    
    if not client:
        raise HTTPException(status_code=500, detail="CallAutomationClient not initialized")
    
    msg_log = [
        "",
        "~~~~~~~~~~~~ /MoveParticipant Operation ~~~~~~~~~~~~"
    ]
    
    try:
        msg_log.extend([
            f"Source Caller Id:     {request.participant_to_move}",
            f"Source Connection Id: {request.source_call_connection_id}",
            f"Target Connection Id: {request.target_call_connection_id}"
        ])
        
        # Get the target connection (where we want to move participants to)
        target_connection = client.get_call_connection(request.target_call_connection_id)
        
        # Create participant identifier based on the input
        if request.participant_to_move.startswith("+"):
            # Phone number
            participant_to_move = PhoneNumberIdentifier(request.participant_to_move)
        elif request.participant_to_move.startswith("8:acs:"):
            # ACS Communication User
            participant_to_move = CommunicationUserIdentifier(request.participant_to_move)
        else:
            raise HTTPException(
                status_code=400, 
                detail="Invalid participant format. Use phone number (+1234567890) or ACS user ID (8:acs:...)"
            )
        # Move the participant        
        response = await target_connection.move_participants(
            target_participants=[participant_to_move],
            from_call=request.source_call_connection_id
        )
        
        if response:
            msg_log.extend(["", "Move Participants operation completed successfully."])
        else:
            raise Exception("Move Participants operation failed")
        
        log_output = "\n".join(msg_log)
        print(log_output)
        
        return PlainTextResponse(content=log_output)
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error in manual move participants operation: {e}"
        print(error_msg)
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": str(e),
                "message": "Move participants operation failed."
            }
        )

@app.get("/GetParticipants/{call_connection_id}", tags=["Move Participants APIs"])
async def get_participants(call_connection_id: str):
    """Get participants for a specific call connection"""
    global client
    
    if not client:
        raise HTTPException(status_code=500, detail="CallAutomationClient not initialized")
    
    msg_log = [
        "",
        f"~~~~~~~~~~~~ /GetParticipants/{call_connection_id} ~~~~~~~~~~~~"
    ]
    
    try:
        call_connection = client.get_call_connection(call_connection_id)
        participants_pager = call_connection.list_participants()
        
        participant_info = []
        participant_count = 0
        
        # Correctly iterate through the AsyncList
        async for participant in participants_pager:
            participant_count += 1
            if hasattr(participant, 'identifier'):
                identifier = participant.identifier
                if isinstance(identifier, PhoneNumberIdentifier):
                    # Use the correct attribute name for phone number
                    # phone_num = getattr(identifier, 'phone_number', getattr(identifier, 'value', 'Unknown'))
                    info = f"{participant_count}. PhoneNumberIdentifier       - RawId: {identifier.raw_id}" #, Phone: {phone_num}
                elif isinstance(identifier, CommunicationUserIdentifier):
                    info = f"{participant_count}. CommunicationUserIdentifier - RawId: {identifier.raw_id}"
                else:
                    info = f"{participant_count}. {type(identifier).__name__} - RawId: {identifier.raw_id}"
                participant_info.append(info)
        
        if participant_count == 0:
            raise HTTPException(
                status_code=404,
                detail={
                    "message": "No participants found for the specified call connection.",
                    "call_connection_id": call_connection_id
                }
            )
        
        msg_log.extend([
            "",
            f"No of Participants: {participant_count}",
            "Participants:",
            "-------------"
        ])
        msg_log.extend(participant_info)
        
        log_output = "\n".join(msg_log)
        print(log_output)
        return PlainTextResponse(content=log_output)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting participants for call {call_connection_id}: {e}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": str(e),
                "call_connection_id": call_connection_id
            }
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
