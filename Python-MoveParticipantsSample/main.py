import logging
import json
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin
from fastapi import FastAPI, HTTPException, status, Body
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel
from azure.eventgrid import EventGridEvent, SystemEventNames
from azure.core.messaging import CloudEvent
from azure.communication.callautomation.aio import CallAutomationClient
from azure.communication.callautomation import (
    PhoneNumberIdentifier,
    CommunicationUserIdentifier
)

# Configuration constants
ACS_CONNECTION_STRING=""
CALLBACK_URI_HOST=""
ACS_OUTBOUND_PHONE_NUMBER=""
ACS_INBOUND_PHONE_NUMBER=""
ACS_USER_PHONE_NUMBER=""
ACS_TEST_IDENTITY2=""
ACS_TEST_IDENTITY3=""

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# FastAPI application setup
app = FastAPI(
    title="Move Participants Sample",
    description="Azure Communication Services Call Automation Move Participants Sample",
    version="1.0.0"
)

# Global state
class AppState:
    def __init__(self):
        self.acs_connection_string = ACS_CONNECTION_STRING
        self.callback_uri_host = CALLBACK_URI_HOST
        self.acs_outbound_phone_number = ACS_OUTBOUND_PHONE_NUMBER
        self.acs_inbound_phone_number = ACS_INBOUND_PHONE_NUMBER
        self.acs_user_phone_number = ACS_USER_PHONE_NUMBER
        self.acs_test_identity2 = ACS_TEST_IDENTITY2
        self.acs_test_identity3 = ACS_TEST_IDENTITY3
        self.last_workflow_call_type = ""
        self.call_connection_id = ""
        self.call_connection_id1 = ""
        self.call_connection_id2 = ""
        self.client: Optional[CallAutomationClient] = None

app_state = AppState()

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

# Utility functions
def initialize_client():
    """Initialize the CallAutomationClient with current configuration"""
    if app_state.acs_connection_string:
        app_state.client = CallAutomationClient.from_connection_string(app_state.acs_connection_string)
        logger.info("Call automation client initialized successfully")
    else:
        logger.warning("Cannot initialize client: ACS connection string not provided")

def get_callback_uri() -> str:
    """Get the callback URI for the application"""
    return urljoin(app_state.callback_uri_host, "/api/callbacks")

def create_participant_identifier(participant_id: str):
    """Create appropriate participant identifier based on input format"""
    if participant_id.startswith("+"):
        return PhoneNumberIdentifier(participant_id)
    elif participant_id.startswith("8:acs:"):
        return CommunicationUserIdentifier(participant_id)
    else:
        raise ValueError("Invalid participant format. Use phone number (+1234567890) or ACS user ID (8:acs:...)")

def extract_caller_ids(event_data: Dict[str, Any]) -> tuple[str, str]:
    """Extract from and to caller IDs from event data"""
    from_caller_id = (event_data['from']["phoneNumber"]["value"] 
                     if event_data['from']['kind'] == "phoneNumber" 
                     else event_data['from']['rawId'])
    to_caller_id = (event_data['to']["phoneNumber"]["value"] 
                   if event_data['to']['kind'] == "phoneNumber" 
                   else event_data['to']['rawId'])
    return from_caller_id, to_caller_id

async def handle_user_incoming_call(incoming_call_data: Dict[str, Any], from_caller_id: str, to_caller_id: str) -> List[str]:
    """Handle incoming call from user"""
    callback_uri = get_callback_uri()
    
    answer_call_result = await app_state.client.answer_call(
        incoming_call_context=incoming_call_data.get("incomingCallContext"),
        callback_url=callback_uri,
        operation_context="IncomingCallFromUser"
    )
    
    app_state.call_connection_id1 = answer_call_result.call_connection_id
    logger.info(f"User call answered - Connection ID: {app_state.call_connection_id1}")
    
    return [
        "User call answered by Call Automation",
        f"From: {from_caller_id}",
        f"To: {to_caller_id}",
        f"Connection ID: {app_state.call_connection_id1}",
        f"Correlation ID: {incoming_call_data.get('correlationId', 'N/A')}"
    ]

async def handle_workflow_call_redirect(incoming_call_data: Dict[str, Any], from_caller_id: str, to_caller_id: str) -> List[str]:
    """Handle workflow call redirection to ACS identities"""
    incoming_call_context = incoming_call_data.get("incomingCallContext")
    
    if app_state.last_workflow_call_type == "CallTwo":
        await app_state.client.redirect_call(
            incoming_call_context=incoming_call_context,
            target_participant=CommunicationUserIdentifier(app_state.acs_test_identity2)
        )
        logger.info(f"Call2 redirected to ACS User Identity 2: {app_state.acs_test_identity2}")
        return [
            f"Call2 redirected to ACS User Identity 2: {app_state.acs_test_identity2}",
            f"From: {from_caller_id}",
            f"To: {to_caller_id}"
        ]
    
    elif app_state.last_workflow_call_type == "CallThree":
        await app_state.client.redirect_call(
            incoming_call_context=incoming_call_context,
            target_participant=CommunicationUserIdentifier(app_state.acs_test_identity3)
        )
        logger.info(f"Call3 redirected to ACS User Identity 3: {app_state.acs_test_identity3}")
        return [
            f"Call3 redirected to ACS User Identity 3: {app_state.acs_test_identity3}",
            f"From: {from_caller_id}",
            f"To: {to_caller_id}"
        ]
    
    else:
        logger.warning(f"Unknown workflow call type: {app_state.last_workflow_call_type}. Using default behavior.")
        await app_state.client.redirect_call(
            incoming_call_context=incoming_call_context,
            target_participant=CommunicationUserIdentifier(app_state.acs_test_identity2)
        )
        return [f"Default: Redirected to ACS User Identity 2: {app_state.acs_test_identity2}"]

def format_response_message(messages: List[str]) -> str:
    """Format response messages for consistent output"""
    return "\n".join(messages)

def validate_client():
    """Validate that the client is initialized"""
    if not app_state.client:
        raise HTTPException(status_code=500, detail="CallAutomationClient not initialized")

# Initialize client on startup
initialize_client()

# API Endpoints
@app.post("/api/MoveParticipantEvent")
async def move_participant_event(events: List[Dict[str, Any]] = Body(...)):
    """Handle Event Grid events for move participants scenario"""
    validate_client()
    
    logger.info("Processing Event Grid events")
    
    try:
        for event_data in events:
            event = EventGridEvent.from_dict(event_data)
            logger.info(f"Processing event: {event.event_type}")
            
            if event.event_type == SystemEventNames.EventGridSubscriptionValidationEventName:
                validation_code = event.data.get("validationCode", "")
                logger.info("Event Grid subscription validation completed")
                return Response(
                    content=json.dumps({"validationResponse": validation_code}),
                    status_code=200, 
                    media_type="application/json"
                )
            
            elif event.event_type == "Microsoft.Communication.IncomingCall":
                from_caller_id, to_caller_id = extract_caller_ids(event.data)
                logger.info(f"Incoming call from {from_caller_id} to {to_caller_id}")
                
                msg_log = []
                
                if app_state.acs_user_phone_number in from_caller_id:
                    msg_log = await handle_user_incoming_call(event.data, from_caller_id, to_caller_id)
                
                elif app_state.acs_inbound_phone_number in from_caller_id:
                    msg_log = await handle_workflow_call_redirect(event.data, from_caller_id, to_caller_id)
                
                response_content = format_response_message(msg_log) if msg_log else "Event processed"
                return Response(content=response_content, status_code=200)
        
        return Response(content="Events processed successfully", status_code=200)

    except Exception as e:
        logger.error(f"Error processing Event Grid event: {e}")
        return Response(content=f"Error: {str(e)}", status_code=500)

@app.post("/api/callbacks")
async def callbacks(events: List[Dict[str, Any]] = Body(...)):
    """Handle Call Automation callback events"""
    validate_client()
    
    msg_log = []
    
    try:
        for event_data in events:
            cloud_event = CloudEvent.from_dict(event_data)
            call_connection_id = cloud_event.data.get('callConnectionId')
            operation_context = cloud_event.data.get('operationContext', '')
            event_type = cloud_event.data.get('type', cloud_event.type)
            
            logger.info(f"Callback event: {event_type}, Context: {operation_context}")
            
            if operation_context and "CallConnected" in event_type:
                if operation_context in ["CallTwo", "CallThree"]:
                    msg_log.extend([
                        f"Call event: CallConnected",
                        f"{operation_context} Connection ID: {call_connection_id}",
                        f"Correlation ID: {cloud_event.data.get('correlationId', 'N/A')}"
                    ])
            
            elif "CallDisconnected" in event_type:
                msg_log.extend([
                    f"Call event: CallDisconnected",
                    f"Connection ID: {call_connection_id}"
                ])
        
        response_content = format_response_message(msg_log) if msg_log else ""
        return PlainTextResponse(content=response_content)
        
    except Exception as e:
        logger.error(f"Error processing callback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/CreateCall1(UserCallToCallAutomation)", tags=["Move Participants APIs"])
async def create_call1():
    """Create Call 1 - User Call to Call Automation"""
    validate_client()
    
    try:
        callback_uri = get_callback_uri()
        caller = PhoneNumberIdentifier(app_state.acs_user_phone_number)
        
        create_call_result = await app_state.client.create_call(
            target_participant=PhoneNumberIdentifier(app_state.acs_inbound_phone_number),
            callback_url=callback_uri,
            source_caller_id_number=caller
        )

        app_state.call_connection_id = create_call_result.call_connection_id
        logger.info(f"Call1 created - Connection ID: {app_state.call_connection_id}")

        messages = [
            "Call 1 (External PSTN to Call Automation):",
            f"From: {app_state.acs_user_phone_number}",
            f"To: {app_state.acs_inbound_phone_number}",
            f"Connection ID: {app_state.call_connection_id}",
            f"Correlation ID: {create_call_result.correlation_id}"
        ]
        
        return PlainTextResponse(content=format_response_message(messages))
        
    except Exception as e:
        logger.error(f"Error creating Call 1: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/CreateCall2(ToPstnUserFirstAndRedirectToAcsIentity)", tags=["Move Participants APIs"])
async def create_call2():
    """Create Call 2 - To PSTN User First And Redirect To ACS Identity"""
    validate_client()
    
    try:
        callback_uri = get_callback_uri()
        caller = PhoneNumberIdentifier(app_state.acs_inbound_phone_number)
        
        create_call_result = await app_state.client.create_call(
            target_participant=PhoneNumberIdentifier(app_state.acs_outbound_phone_number),
            callback_url=callback_uri,
            source_caller_id_number=caller,
            operation_context="CallTwo"
        )
        
        app_state.last_workflow_call_type = "CallTwo"
        app_state.call_connection_id1 = create_call_result.call_connection_id
        logger.info(f"Call2 created - Connection ID: {app_state.call_connection_id1}")

        messages = [
            "Call 2:",
            f"From: {app_state.acs_inbound_phone_number}",
            f"To: {app_state.acs_outbound_phone_number}",
            f"Connection ID: {app_state.call_connection_id1}",
            f"Correlation ID: {create_call_result.correlation_id}",
            f"Will redirect to: {app_state.acs_test_identity2}"
        ]
        
        return PlainTextResponse(content=format_response_message(messages))
        
    except Exception as e:
        logger.error(f"Error creating Call 2: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/CreateCall3(ToPstnUserFirstAndRedirectToAcsIentity)", tags=["Move Participants APIs"])
async def create_call3():
    """Create Call 3 - To PSTN User First And Redirect To ACS Identity"""
    validate_client()
    
    try:
        callback_uri = get_callback_uri()
        caller = PhoneNumberIdentifier(app_state.acs_inbound_phone_number)

        create_call_result = await app_state.client.create_call(
            target_participant=PhoneNumberIdentifier(app_state.acs_outbound_phone_number),
            callback_url=callback_uri,
            source_caller_id_number=caller,
            operation_context="CallThree"
        )

        app_state.last_workflow_call_type = "CallThree"
        app_state.call_connection_id2 = create_call_result.call_connection_id
        logger.info(f"Call3 created - Connection ID: {app_state.call_connection_id2}")

        messages = [
            "Call 3:",
            f"From: {app_state.acs_inbound_phone_number}",
            f"To: {app_state.acs_outbound_phone_number}",
            f"Connection ID: {app_state.call_connection_id2}",
            f"Correlation ID: {create_call_result.correlation_id}",
            f"Will redirect to: {app_state.acs_test_identity3}"
        ]
        
        return PlainTextResponse(content=format_response_message(messages))
        
    except Exception as e:
        logger.error(f"Error creating Call 3: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/MoveParticipant", tags=["Move Participants APIs"])
async def move_participant(request: MoveParticipantsRequest):
    """Move participants between calls"""
    validate_client()
    
    try:
        logger.info(f"Moving participant {request.participant_to_move} from {request.source_call_connection_id} to {request.target_call_connection_id}")
        
        target_connection = app_state.client.get_call_connection(request.target_call_connection_id)
        participant_to_move = create_participant_identifier(request.participant_to_move)
        
        response = await target_connection.move_participants(
            target_participants=[participant_to_move],
            from_call=request.source_call_connection_id
        )
        
        if response:
            logger.info("Move participants operation completed successfully")
            messages = [
                "Move Participant Operation:",
                f"Participant: {request.participant_to_move}",
                f"From: {request.source_call_connection_id}",
                f"To: {request.target_call_connection_id}",
                "Status: Success"
            ]
        else:
            raise Exception("Move participants operation failed")
        
        return PlainTextResponse(content=format_response_message(messages))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in move participants operation: {e}")
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": str(e),
                "message": "Move participants operation failed"
            }
        )

@app.get("/GetParticipants/{call_connection_id}", tags=["Move Participants APIs"])
async def get_participants(call_connection_id: str):
    """Get participants for a specific call connection"""
    validate_client()
    
    try:
        call_connection = app_state.client.get_call_connection(call_connection_id)
        participants_pager = call_connection.list_participants()
        
        participant_info = []
        participant_count = 0
        
        async for participant in participants_pager:
            participant_count += 1
            if hasattr(participant, 'identifier'):
                identifier = participant.identifier
                if isinstance(identifier, PhoneNumberIdentifier):
                    info = f"{participant_count}. PhoneNumberIdentifier - RawId: {identifier.raw_id}"
                elif isinstance(identifier, CommunicationUserIdentifier):
                    info = f"{participant_count}. CommunicationUserIdentifier - RawId: {identifier.raw_id}"
                else:
                    info = f"{participant_count}. {type(identifier).__name__} - RawId: {identifier.raw_id}"
                participant_info.append(info)
        
        if participant_count == 0:
            raise HTTPException(
                status_code=404,
                detail={
                    "message": "No participants found for the specified call connection",
                    "call_connection_id": call_connection_id
                }
            )
        
        logger.info(f"Retrieved {participant_count} participants for call {call_connection_id}")
        
        messages = [
            f"Participants for Call {call_connection_id}:",
            f"Count: {participant_count}",
            ""] + participant_info
        
        return PlainTextResponse(content=format_response_message(messages))
        
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
    uvicorn.run(app, host="0.0.0.0", port=8080)