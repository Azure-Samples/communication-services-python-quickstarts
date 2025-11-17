import json
import logging
import os
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from azure.communication.callautomation import (
    CommunicationUserIdentifier,
    PhoneNumberIdentifier,
    TextSource,
)
from azure.communication.callautomation.aio import CallAutomationClient
from azure.core.messaging import CloudEvent
from azure.eventgrid import EventGridEvent, SystemEventNames
from fastapi import Body, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel

# Configuration constants
ACS_CONNECTION_STRING = "endpoint=https://dacsrecordingtest.unitedstates.communication.azure.com/;accesskey=9lMdkVL4KcqJ3YXGgWS9Fxa1CjPwXs63rEMczJ7DsC9mbWR3hlbtJQQJ99BEACULyCpAArohAAAAAZCS58G3"
COGNITIVE_SERVICES_ENDPOINT = "https://cognitive-service-waferwire.cognitiveservices.azure.com/"
CALLBACK_URI_HOST = "https://smp64787.inc1.devtunnels.ms:8080"
ACS_LOBBY_CALL_RECEIVER = "8:acs:19ae37ff-1a44-4e19-aade-198eedddbdf2_0000002b-318d-04f0-5de5-6f8ded7ce95b"
ACS_TARGET_CALL_RECEIVER = "8:acs:19ae37ff-1a44-4e19-aade-198eedddbdf2_0000002b-318d-7df4-23e1-6f8ded7cdd0f"
ACS_TARGET_CALL_SENDER = "8:acs:19ae37ff-1a44-4e19-aade-198eedddbdf2_0000002b-324e-86be-91ef-6f8ded7cf4fa"

# Default messages
CONFIRM_MESSAGE_TO_TARGET_CALL = (
    "A user is waiting in lobby, do you want to add the lobby user to your call?"
)
TEXT_TO_PLAY_TO_LOBBY_USER = (
    "You are currently in a lobby call, we will notify the admin that you are waiting."
)

def validate_environment_variables() -> List[str]:
    """Validate required environment variables and return missing ones."""
    required_vars = [
        ("ACS_CONNECTION_STRING", ACS_CONNECTION_STRING),
        ("CALLBACK_URI_HOST", CALLBACK_URI_HOST),
        ("COGNITIVE_SERVICES_ENDPOINT", COGNITIVE_SERVICES_ENDPOINT),
        ("ACS_LOBBY_CALL_RECEIVER", ACS_LOBBY_CALL_RECEIVER),
        ("ACS_TARGET_CALL_RECEIVER", ACS_TARGET_CALL_RECEIVER),
        ("ACS_TARGET_CALL_SENDER", ACS_TARGET_CALL_SENDER),
    ]
    return [var_name for var_name, var_value in required_vars if not var_value]


def initialize_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


# Validate environment and initialize logging
missing_vars = validate_environment_variables()
if missing_vars:
    print(f"Warning: Missing environment variables: {', '.join(missing_vars)}")
    print("Use the /setConfigurations endpoint to set these values after startup.")

initialize_logging()
logger = logging.getLogger(__name__)

# FastAPI application setup
app = FastAPI(
    title="Lobby Call Support Sample",
    description="Azure Communication Services Call Automation Lobby Call Support Sample",
    version="1.0.0",
)

# Application state
class ApplicationState:
    """Centralized application state management."""
    
    def __init__(self):
        # Configuration
        self.acs_connection_string: str = ACS_CONNECTION_STRING
        self.callback_uri_host: str = CALLBACK_URI_HOST
        self.acs_lobby_call_receiver: str = ACS_LOBBY_CALL_RECEIVER
        self.acs_target_call_receiver: str = ACS_TARGET_CALL_RECEIVER
        self.acs_target_call_sender: str = ACS_TARGET_CALL_SENDER
        self.confirm_message_to_target_call: str = CONFIRM_MESSAGE_TO_TARGET_CALL
        self.text_to_play_to_lobby_user: str = TEXT_TO_PLAY_TO_LOBBY_USER
        
        # Call tracking
        self.target_call_connection_id: str = ""
        self.lobby_connection_id: str = ""
        self.lobby_caller_id: str = ""
        
        # WebSocket connection
        self.websocket_connection: Optional[WebSocket] = None


app_state = ApplicationState()

def initialize_call_automation_client(connection_string: str) -> Optional[CallAutomationClient]:
    """Initialize CallAutomationClient with proper error handling."""
    try:
        if connection_string:
            return CallAutomationClient.from_connection_string(connection_string)
        logger.warning("CallAutomationClient not initialized - missing connection string")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize CallAutomationClient: {e}")
        return None


# Initialize CallAutomationClient
client = initialize_call_automation_client(ACS_CONNECTION_STRING)

# Pydantic models
class ConfigurationRequest(BaseModel):
    """Request model for updating application configuration."""
    
    acs_connection_string: Optional[str] = None
    callback_uri_host: Optional[str] = None
    acs_lobby_call_receiver: Optional[str] = None
    acs_target_call_receiver: Optional[str] = None
    acs_target_call_sender: Optional[str] = None
    confirm_message_to_target_call: Optional[str] = None
    text_to_play_to_lobby_user: Optional[str] = None


class TargetCallRequest(BaseModel):
    """Request model for creating a target call."""
    
    acs_target: str
# Event Handler
@app.post("/api/LobbyCallSupportEventHandler")
async def lobby_call_support_event_handler(events: List[Dict[str, Any]] = Body(...)):
    """Handle Event Grid events for lobby call support scenario."""
    if not client:
        raise HTTPException(status_code=500, detail="Call automation client not initialized")
    
    try:
        for event_data in events:
            event = EventGridEvent.from_dict(event_data)
            
            if event.event_type == SystemEventNames.EventGridSubscriptionValidationEventName:
                validation_code = event.data.get("validationCode", "")
                return Response(
                    content=json.dumps({"validationResponse": validation_code}),
                    status_code=200,
                    media_type="application/json",
                )
            
            elif event.event_type == "Microsoft.Communication.IncomingCall":
                incoming_call_data = event.data
                logger.info(f"Event received: {event.event_type}")
                
                from_caller_id = (
                    event.data['from']["phoneNumber"]["value"]
                    if event.data['from']['kind'] == "phoneNumber"
                    else event.data['from']['rawId']
                )
                to_caller_id = (
                    event.data['to']["phoneNumber"]["value"]
                    if event.data['to']['kind'] == "phoneNumber"
                    else event.data['to']['rawId']
                )
                
                # Check if this is a lobby or target call
                if (app_state.acs_lobby_call_receiver in to_caller_id or 
                    app_state.acs_target_call_receiver in to_caller_id):
                    
                    callback_uri = urljoin(app_state.callback_uri_host, "/api/callbacks")
                    operation_context = (
                        "LobbyCall" 
                        if app_state.acs_target_call_receiver not in to_caller_id 
                        else "OtherCall"
                    )
                    
                    answer_call_result = await client.answer_call(
                        incoming_call_context=incoming_call_data.get("incomingCallContext"),
                        callback_url=callback_uri,
                        operation_context=operation_context,
                        cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT,
                    )
                    
                    if app_state.acs_target_call_receiver in to_caller_id:
                        app_state.target_call_connection_id = answer_call_result.call_connection_id
                        logger.info(f"Target call answered: {app_state.target_call_connection_id}")
                    else:
                        app_state.lobby_connection_id = answer_call_result.call_connection_id
                        logger.info(f"Lobby call answered: {app_state.lobby_connection_id}")
        
        return PlainTextResponse(content="Events processed successfully")

    except Exception as e:
        logger.error(f"Error processing lobby call support event: {e}")
        return Response(content=str(e), status_code=500)

@app.post("/api/callbacks")
async def callbacks(events: List[Dict[str, Any]] = Body(...)):
    """Handle Call Automation callback events."""
    if not client:
        raise HTTPException(status_code=500, detail="Call automation client not initialized")
    
    try:
        for event_data in events:
            cloud_event = CloudEvent.from_dict(event_data)
            operation_context = cloud_event.data.get('operationContext', '')
            event_type = cloud_event.data.get('type', cloud_event.type)
            call_connection_id = (
                cloud_event.data.get('callConnectionId') or 
                cloud_event.data["callConnectionId"]
            )
            
            logger.info(f"Received callback event: {event_type}, Context: {operation_context}")
            
            # Handle CallConnected event
            if "CallConnected" in event_type:
                if operation_context == "LobbyCall":
                    # Get lobby caller information
                    lobby_call_connection = client.get_call_connection(call_connection_id)
                    call_properties = await lobby_call_connection.get_call_properties()
                    app_state.lobby_caller_id = call_properties.source.raw_id
                    app_state.lobby_connection_id = call_properties.call_connection_id
                    
                    # Play message to lobby user
                    text_source = TextSource(
                        text=app_state.text_to_play_to_lobby_user,
                        voice_name="en-US-NancyNeural"
                    )
                    await lobby_call_connection.play_media(
                        play_source=[text_source],
                        play_to=[CommunicationUserIdentifier(app_state.lobby_caller_id)]
                    )
                    
            # Handle PlayCompleted event
            elif "PlayCompleted" in event_type:
                # Notify target call user via WebSocket
                if app_state.websocket_connection is None:
                    logger.warning("WebSocket connection not available")
                    return Response(content="WebSocket not available", status_code=404)

                await app_state.websocket_connection.send_text(
                    app_state.confirm_message_to_target_call
                )
                logger.info("Target call user notified via WebSocket")
                return Response(content="Target call user notified")
            
            # Handle MoveParticipantSucceeded event
            elif "MoveParticipantSucceeded" in event_type:
                logger.info(f"Participant moved successfully: {call_connection_id}")

            # Handle CallDisconnected event
            elif "CallDisconnected" in event_type:
                logger.info(f"Call disconnected: {call_connection_id}")
        
        return PlainTextResponse(content="Callbacks processed successfully")
            
    except Exception as e:
        logger.error(f"Error processing callback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/TargetCallToAcsUser", tags=["Lobby Call Support APIs"])
async def target_call_to_acs_user(request: TargetCallRequest):
    """Create Target Call to ACS User."""
    if not client:
        raise HTTPException(status_code=500, detail="Call automation client not initialized")
    
    try:
        callback_uri = urljoin(app_state.callback_uri_host, "/api/callbacks")
        
        create_call_result = await client.create_call(
            target_participant=CommunicationUserIdentifier(request.acs_target),
            callback_url=callback_uri
        )

        app_state.target_call_connection_id = create_call_result.call_connection_id
        
        logger.info(f"Target call created: {app_state.target_call_connection_id}")
        return {
            "message": "Target call created successfully",
            "call_connection_id": app_state.target_call_connection_id,
            "correlation_id": create_call_result.correlation_id
        }
        
    except Exception as e:
        logger.error(f"Error creating target call: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/GetParticipants/{call_connection_id}", tags=["Lobby Call Support APIs"])
async def get_participants(call_connection_id: str):
    """Get participants for a specific call connection."""
    if not client:
        raise HTTPException(status_code=500, detail="Call automation client not initialized")
    
    try:
        call_connection = client.get_call_connection(call_connection_id)
        participants_paged = call_connection.list_participants()
        
        participants = []
        async for participant in participants_paged:
            identifier = participant.identifier
            
            if isinstance(identifier, PhoneNumberIdentifier):
                phone_num = getattr(identifier, 'phone_number', 'Unknown')
                participant_info = {
                    "type": "PhoneNumberIdentifier",
                    "raw_id": identifier.raw_id,
                    "phone_number": phone_num
                }
            elif isinstance(identifier, CommunicationUserIdentifier):
                participant_info = {
                    "type": "CommunicationUserIdentifier",
                    "raw_id": identifier.raw_id
                }
            else:
                participant_info = {
                    "type": type(identifier).__name__,
                    "raw_id": identifier.raw_id
                }
            
            participants.append(participant_info)
        
        if not participants:
            raise HTTPException(
                status_code=404,
                detail="No participants found for the specified call connection"
            )
        
        return {
            "call_connection_id": call_connection_id,
            "participant_count": len(participants),
            "participants": participants
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting participants for call {call_connection_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication with client app."""
    if not client:
        await websocket.close(code=1000, reason="Call automation client not initialized")
        return
    
    await websocket.accept()
    app_state.websocket_connection = websocket
    logger.info("WebSocket connection established")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            logger.info(f"Received WebSocket message: {data}")
            
            # Process incoming message
            if data.lower() == "yes":
                await _handle_move_participant()
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
        app_state.websocket_connection = None
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        app_state.websocket_connection = None


async def _handle_move_participant():
    """Handle moving participant from lobby to target call."""
    try:
        if not all([app_state.lobby_caller_id, app_state.lobby_connection_id, 
                   app_state.target_call_connection_id]):
            logger.error("Missing required call information for move operation")
            return
        
        logger.info(f"Moving participant {app_state.lobby_caller_id} from lobby to target call")
        
        # Get the target connection and move the participant
        target_connection = client.get_call_connection(app_state.target_call_connection_id)
        response = await target_connection.move_participants(
            target_participants=[CommunicationUserIdentifier(app_state.lobby_caller_id)],
            from_call=app_state.lobby_connection_id
        )
        
        logger.info("Move participants operation completed successfully")
        
    except Exception as e:
        logger.error(f"Error in move participants operation: {e}")

def main():
    """Main entry point for the application."""
    import uvicorn
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    main()
