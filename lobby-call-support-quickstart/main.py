import os
import logging
import json
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin
from fastapi import FastAPI, HTTPException, WebSocket, status, Body, WebSocketDisconnect
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from azure.eventgrid import EventGridEvent, SystemEventNames
from azure.core.messaging import CloudEvent
from azure.communication.callautomation.aio import CallAutomationClient
from azure.communication.callautomation import (
    PhoneNumberIdentifier,
    CommunicationUserIdentifier,
    TextSource
)
from fastapi.responses import Response

# ACS Connection String and other configurations; TO BE UPDATED BEFORE RUNNING THE APP
# For local development, you can use environment variables or a .env file.
ACS_CONNECTION_STRING = os.getenv("ACS_CONNECTION_STRING", "")
COGNITIVE_SERVICES_ENDPOINT = os.getenv("COGNITIVE_SERVICES_ENDPOINT", "")
# Callback URI host for ACS Call Automation
CALLBACK_URI_HOST = os.getenv("CALLBACK_URI_HOST", "")
# ACS Generated IDs for Call Automation
ACS_GENERATED_ID_FOR_LOBBY_CALL_RECEIVER = os.getenv("ACS_GENERATED_ID_FOR_LOBBY_CALL_RECEIVER", "")
ACS_GENERATED_ID_FOR_TARGET_CALL_RECEIVER = os.getenv("ACS_GENERATED_ID_FOR_TARGET_CALL_RECEIVER", "")
ACS_GENERATED_ID_FOR_TARGET_CALL_SENDER = os.getenv("ACS_GENERATED_ID_FOR_TARGET_CALL_SENDER", "")
# Confirmation message to Target Call users
CONFIRM_MESSAGE_TO_TARGET_CALL = "A user is waiting in lobby, do you want to add the lobby user to your call?"
# Text to play to Lobby User
TEXT_TO_PLAY_TO_LOBBY_USER =  "You are currently in a lobby call, we will notify the admin that you are waiting."

# Validate required environment variables
required_vars = [
    ("ACS_CONNECTION_STRING", ACS_CONNECTION_STRING),
    ("CALLBACK_URI_HOST", CALLBACK_URI_HOST),
    ("COGNITIVE_SERVICES_ENDPOINT", COGNITIVE_SERVICES_ENDPOINT),
    ("ACS_GENERATED_ID_FOR_LOBBY_CALL_RECEIVER", ACS_GENERATED_ID_FOR_LOBBY_CALL_RECEIVER),
    ("ACS_GENERATED_ID_FOR_TARGET_CALL_RECEIVER", ACS_GENERATED_ID_FOR_TARGET_CALL_RECEIVER),
    ("ACS_GENERATED_ID_FOR_TARGET_CALL_SENDER", ACS_GENERATED_ID_FOR_TARGET_CALL_SENDER)
]

missing_vars = [var_name for var_name, var_value in required_vars if not var_value]
if missing_vars:
    print(f"Warning: Missing environment variables: {', '.join(missing_vars)}")
    print("The application will start but may not function properly without proper configuration.")
    print("Use the /setConfigurations endpoint to set these values after startup.")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bootstrap - FastAPI application setup
app = FastAPI(
    title="Lobby Call Support Sample",
    description="Azure Communication Services Call Automation Lobby Call Support Sample",
    version="1.0.0"
)

# Global Variables for Lobby Call Support Scenario
acs_connection_string: str = ACS_CONNECTION_STRING
callback_uri_host: str = CALLBACK_URI_HOST
acs_generated_id_for_lobby_call_receiver: str = ACS_GENERATED_ID_FOR_LOBBY_CALL_RECEIVER
acs_generated_id_for_target_call_receiver: str = ACS_GENERATED_ID_FOR_TARGET_CALL_RECEIVER
acs_generated_id_for_target_call_sender: str = ACS_GENERATED_ID_FOR_TARGET_CALL_SENDER
confirm_message_to_target_call: str = CONFIRM_MESSAGE_TO_TARGET_CALL
text_to_play_to_lobby_user: str = TEXT_TO_PLAY_TO_LOBBY_USER

# Track workflow state
last_workflow_call_type: str = ""
acs_identity: str = ""

# Call connection IDs
target_call_connection_id: str = ""
lobby_connection_id: str = ""  # User's incoming call connection id
lobby_caller_id: str = ""  # User's incoming caller id
call_connection_id2: str = ""  # Additional call connection id

# WebSocket connection
websocket_connection: Optional[WebSocket] = None

# Initialize CallAutomationClient
client = None
try:
    if ACS_CONNECTION_STRING:
        client = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)
    else:
        print("Warning: CallAutomationClient not initialized - missing ACS_CONNECTION_STRING")
except Exception as e:
    print(f"Warning: Failed to initialize CallAutomationClient: {e}")
    print("Use the /setConfigurations endpoint to set proper connection string.")

# Pydantic models
class ConfigurationRequest(BaseModel):
    acs_connection_string: Optional[str] = None
    callback_uri_host: Optional[str] = None
    acs_generated_id_for_lobby_call_receiver: Optional[str] = None
    acs_generated_id_for_target_call_receiver: Optional[str] = None
    acs_generated_id_for_target_call_sender: Optional[str] = None
    confirm_message_to_target_call: Optional[str] = None
    text_to_play_to_lobby_user: Optional[str] = None

class TargetCallRequest(BaseModel):
    acs_target: str

# Configuration Endpoint
@app.post("/setConfigurations", tags=["Configuration"])
async def set_configurations(configuration_request: ConfigurationRequest):
    """Set configuration values for the application"""
    global acs_connection_string, callback_uri_host, client
    global acs_generated_id_for_lobby_call_receiver, acs_generated_id_for_target_call_receiver
    global acs_generated_id_for_target_call_sender, confirm_message_to_target_call, text_to_play_to_lobby_user
    
    try:
        if configuration_request.acs_connection_string:
            acs_connection_string = configuration_request.acs_connection_string
            client = CallAutomationClient.from_connection_string(acs_connection_string)
        if configuration_request.callback_uri_host:
            callback_uri_host = configuration_request.callback_uri_host
        if configuration_request.acs_generated_id_for_lobby_call_receiver:
            acs_generated_id_for_lobby_call_receiver = configuration_request.acs_generated_id_for_lobby_call_receiver
        if configuration_request.acs_generated_id_for_target_call_receiver:
            acs_generated_id_for_target_call_receiver = configuration_request.acs_generated_id_for_target_call_receiver
        if configuration_request.acs_generated_id_for_target_call_sender:
            acs_generated_id_for_target_call_sender = configuration_request.acs_generated_id_for_target_call_sender
        if configuration_request.confirm_message_to_target_call:
            confirm_message_to_target_call = configuration_request.confirm_message_to_target_call
        if configuration_request.text_to_play_to_lobby_user:
            text_to_play_to_lobby_user = configuration_request.text_to_play_to_lobby_user
        
        log_msg = "Configuration is set successfully.\nInitialized call automation client."
        print(log_msg)
        return {"message": log_msg}
        
    except Exception as e:
        logger.error(f"Error setting configuration: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# Event Handler
@app.post("/api/LobbyCallSupportEventHandler")
async def lobby_call_support_event_handler(events: List[Dict[str, Any]] = Body(...)):
    """Handle Event Grid events for lobby call support scenario"""
    global lobby_connection_id, target_call_connection_id, acs_identity, client
    
    msg_log = ["\n~~~~~~~~~~~~ /api/LobbyCallSupportEventHandler ~~~~~~~~~~~~"]

    try:
        for event_data in events:
            event = EventGridEvent.from_dict(event_data)
            
            if event.event_type == SystemEventNames.EventGridSubscriptionValidationEventName:
                validation_data = event.data
                validation_code = validation_data.get("validationCode", "")
                return Response(
                    content=json.dumps({"validationResponse": validation_code}),
                    status_code=200, 
                    media_type="application/json"
                )
            
            elif event.event_type == "Microsoft.Communication.IncomingCall":
                incoming_call_data = event.data
                msg_log.append(f"Event received: {event.event_type}")
                
                from_caller_id = event.data['from']["phoneNumber"]["value"] if event.data['from']['kind'] =="phoneNumber" else event.data['from']['rawId']
                to_caller_id = event.data['to']["phoneNumber"]["value"] if event.data['to']['kind'] =="phoneNumber" else event.data['to']['rawId']
                # Lobby Call or Target Call: Answer 
                if (acs_generated_id_for_lobby_call_receiver in to_caller_id or 
                    acs_generated_id_for_target_call_receiver in to_caller_id):
                    callback_uri = urljoin(callback_uri_host, "/api/callbacks")
                    operation_context = "LobbyCall" if acs_generated_id_for_target_call_receiver not in to_caller_id else "OtherCall"
                    
                    answer_call_result = await client.answer_call(
                        incoming_call_context=incoming_call_data.get("incomingCallContext"),
                        callback_url=callback_uri,
                        operation_context=operation_context,
                        cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT,
                    )
                    
                    if acs_generated_id_for_target_call_receiver in to_caller_id:
                        target_call_connection_id = answer_call_result.call_connection_id
                        
                        msg_log.extend([
                            "Target Call(Inbound) Answered by Call Automation.",
                            f"From Caller Raw Id: {from_caller_id}",
                            f"To Caller Raw Id:   {to_caller_id}",
                            f"Target Call Connection Id: {target_call_connection_id}",
                            f"Correlation Id:           {incoming_call_data.get('correlationId', '')}",
                            "Target Call answered successfully."
                        ])
                    else:
                        lobby_connection_id = answer_call_result.call_connection_id
                        
                        msg_log.extend([
                            "User Call(Inbound) Answered by Call Automation.",
                            f"From Caller Raw Id: {from_caller_id}",
                            f"To Caller Raw Id:   {to_caller_id}",
                            f"Lobby Call Connection Id: {lobby_connection_id}",
                            f"Correlation Id:           {incoming_call_data.get('correlationId', '')}",
                            "Lobby Call answered successfully."
                        ])
        
        log_to_send = "\n".join(msg_log)
        print(log_to_send)
        return PlainTextResponse(content=log_to_send)

    except Exception as e:
        logger.error(f"Error processing lobby call support event: {e}")
        return Response(content=str(e), status_code=500)

# Callback Handler
@app.post("/api/callbacks")
async def callbacks(events: List[Dict[str, Any]] = Body(...)):
    """Handle Call Automation callback events"""
    global client, lobby_caller_id, lobby_connection_id, websocket_connection
    
    msg_log = []
    
    try:
        for event_data in events:
            cloud_event = CloudEvent.from_dict(event_data)            
            operation_context = cloud_event.data.get('operationContext', '')
            print(f"Operation Context: {operation_context}")
            event_type = cloud_event.data.get('type', cloud_event.type)
            call_connection_id = cloud_event.data.get('callConnectionId') or cloud_event.data["callConnectionId"]
            
            # Handle CallConnected event
            if "CallConnected" in event_type:
                print(f"~~~~~~~~~~~~  /api/callbacks ~~~~~~~~~~~~")
                print(f"Received callConnected.CallConnectionId : {call_connection_id}")

                if operation_context == "LobbyCall":
                    msg_log.extend([
                        "~~~~~~~~~~~~  /api/callbacks ~~~~~~~~~~~~",
                        f"Received call event  : {event_type}",
                        f"Lobby Call Connection Id: {event_type}",
                        f"Correlation Id:           {getattr(event_type, 'correlation_id', '')}"
                    ])

                    # Record lobby caller id and connection id 
                    lobby_call_connection = client.get_call_connection(call_connection_id)
                    call_connection_properties = await lobby_call_connection.get_call_properties()
                    lobby_caller_id = call_connection_properties.source.raw_id
                    lobby_connection_id = call_connection_properties.call_connection_id
                    
                    print(f"Lobby Caller Id:     {lobby_caller_id}")
                    print(f"Lobby Connection Id: {lobby_connection_id}")
                    
                    text_source = TextSource(
                        text=text_to_play_to_lobby_user,
                        voice_name="en-US-NancyNeural"
                    )
                    await lobby_call_connection.play_media(
                        play_source=[text_source], 
                        play_to=[CommunicationUserIdentifier(lobby_caller_id)]
                    )
                    
            # Handle PlayCompleted event
            elif "PlayCompleted" in event_type:
                msg_log.extend([
                    "~~~~~~~~~~~~  /api/callbacks ~~~~~~~~~~~~",
                    f"Received event: {event_type}"
                ])
                print([
                    "~~~~~~~~~~~~  /api/callbacks ~~~~~~~~~~~~",
                    f"Received event: {event_type}"
                ])

                # Notify Target Call user via WebSocket
                if websocket_connection is None:
                    msg_log.append("ERROR: Web socket is not available.")
                    return Response(content="Message not sent", status_code=404)

                # Notify Client
                await websocket_connection.send_text(confirm_message_to_target_call)
                msg_log.append(f"Target Call notified with message: {confirm_message_to_target_call}")
                return Response(content=f"Target Call notified with message: {confirm_message_to_target_call}")
            
            # Handle MoveParticipantSucceeded event
            elif "MoveParticipantSucceeded" in event_type:
                msg_log.extend([
                    "~~~~~~~~~~~~  /api/callbacks ~~~~~~~~~~~~",
                    f"Received event: {event_type}",
                    f"Call Connection Id: {call_connection_id}",
                    f"Correlation Id:      {getattr(event_type, 'correlation_id', '')}"
                ])
            
                print([
                    "~~~~~~~~~~~~  /api/callbacks ~~~~~~~~~~~~",
                    f"Received event: {event_type}",
                    f"Call Connection Id: {call_connection_id}",
                    f"Correlation Id:      {getattr(event_type, 'correlation_id', '')}"
                ])

            # Handle CallDisconnected event
            elif "CallDisconnected" in event_type:
                msg_log.extend([
                    "~~~~~~~~~~~~  /api/callbacks ~~~~~~~~~~~~",
                    f"Received event: {event_type}",
                    f"Call Connection Id: {call_connection_id}",
                    f"Correlation Id:      {getattr(event_type, 'correlation_id', '')}"
                ])               
            
                print([
                    "~~~~~~~~~~~~  /api/callbacks ~~~~~~~~~~~~",
                    f"Received event: {event_type}",
                    f"Call Connection Id: {call_connection_id}",
                    f"Correlation Id:      {getattr(event_type, 'correlation_id', '')}"
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

# Lobby Call Support Workflow Endpoints
@app.post("/TargetCallToAcsUser(Call Replaced with client app)", tags=["Lobby Call Support APIs"])
async def target_call_to_acs_user(request: TargetCallRequest):
    """Create Target Call to ACS User"""
    global target_call_connection_id, client
    
    msg_log = [
        "",
        "~~~~~~~~~~~~ /TargetCall(Create)  ~~~~~~~~~~~~"
    ]
    
    try:
        callback_uri = urljoin(callback_uri_host, "/api/callbacks")
        
        create_call_result = await client.create_call(
            target_participant=CommunicationUserIdentifier(request.acs_target),
            callback_url=callback_uri
        )

        target_call_connection_id = create_call_result.call_connection_id

        msg_log.extend([
            "TargetCall:",
            "-----------",
            f"From: Call Automation",
            f"To:   {request.acs_target}",
            f"Target Call Connection Id: {target_call_connection_id}",
            f"Correlation Id:            {create_call_result.correlation_id}"
        ])
        
        log_output = "\n".join(msg_log)
        print(log_output)
        return PlainTextResponse(content=log_output)
        
    except Exception as e:
        logger.error(f"Error creating target call: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/GetParticipants/{call_connection_id}", tags=["Lobby Call Support APIs"])
async def get_participants(call_connection_id: str):
    """Get participants for a specific call connection"""
    global client
    
    msg_log = [
        "",
        f"~~~~~~~~~~~~ /GetParticipants/{call_connection_id} ~~~~~~~~~~~~"
    ]
    
    try:
        call_connection = client.get_call_connection(call_connection_id)
        participants_paged = call_connection.list_participants()
        
        participant_info = []
        participant_count = 0
        
        async for participant in participants_paged:
            participant_count += 1
            identifier = participant.identifier
            
            if isinstance(identifier, PhoneNumberIdentifier):
                phone_num = getattr(identifier, 'phone_number', 'Unknown')
                info = f"PhoneNumberIdentifier       - RawId: {identifier.raw_id}, Phone: {phone_num}"
            elif isinstance(identifier, CommunicationUserIdentifier):
                info = f"CommunicationUserIdentifier - RawId: {identifier.raw_id}"
            else:
                info = f"{type(identifier).__name__} - RawId: {identifier.raw_id}"
            
            participant_info.append(f"{participant_count}. {info}")
        
        if participant_count == 0:
            return Response(
                content=json.dumps({
                    "Message": "No participants found for the specified call connection.",
                    "CallConnectionId": call_connection_id
                }),
                status_code=404,
                media_type="application/json"
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
        
    except Exception as e:
        logger.error(f"Error getting participants for call {call_connection_id}: {e}")
        return Response(
            content=json.dumps({
                "Error": str(e),
                "CallConnectionId": call_connection_id
            }),
            status_code=400,
            media_type="application/json"
        )

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication with client app"""
    global websocket_connection, lobby_caller_id, lobby_connection_id, target_call_connection_id
    
    print("Received WEB SOCKET request.")
    await websocket.accept()
    websocket_connection = websocket
    print("WebSocket connection established")
    
    try:
        # Keep alive with a read loop
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            print(f"Received response from Client App: {data}")
            
            # Process incoming message
            if data.lower() == "yes":
                print("Move Participant operation begins..")
                
                try:
                    print(f"""
                    ~~~~~~~~~~~~  /api/callbacks ~~~~~~~~~~~~
                    Move Participant operation started..
                    Source Caller Id:     {lobby_caller_id}
                    Source Connection Id: {lobby_connection_id}
                    Target Connection Id: {target_call_connection_id}
                    """)

                    # Get the target connection
                    target_connection = client.get_call_connection(target_call_connection_id)
                    # Move the participant from lobby to target call
                    response = await target_connection.move_participants(
                        target_participants=[CommunicationUserIdentifier(lobby_caller_id)],
                        from_call=lobby_connection_id
                    )
                    
                    print("")
                    print("Move Participants operation completed successfully.")
                    print(f"Operation ID: {response.operation_id if hasattr(response, 'operation_id') else 'N/A'}")
                    
                except Exception as ex:
                    logger.error(f"Error in move participants operation: {ex}")
    
    except WebSocketDisconnect:
        print("WebSocket disconnected")
        websocket_connection = None
    except Exception as ex:
        logger.error("----- Web socket error -----")
        logger.error(str(ex))
        logger.error("----- End: Web socket error -----")
        websocket_connection = None

if __name__ == "__main__":
    import uvicorn
    # Configure for development with WebSocket support
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8080,
        log_level="info",
        access_log=True
    )
