import time
from quart import Quart, render_template, jsonify, request, redirect
from azure.core.exceptions import HttpResponseError
from datetime import datetime, timezone, timedelta
from azure.communication.callautomation import (
    PhoneNumberIdentifier,
    TextSource
)
from azure.communication.identity import (
    CommunicationUserIdentifier,
    CommunicationIdentityClient
)
from azure.communication.callautomation.aio import (
    CallAutomationClient
    )
from azure.communication.rooms import (
    RoomsClient,
    RoomParticipant,
    ParticipantRole
)

from logging import INFO
import asyncio
from config import Config

# Initialize Quart app
app = Quart(__name__)

# Use config values from config.py
PORT = Config.PORT
CONNECTION_STRING = Config.CONNECTION_STRING
ACS_RESOURCE_PHONE_NUMBER = Config.ACS_RESOURCE_PHONE_NUMBER
TARGET_PHONE_NUMBER = Config.TARGET_PHONE_NUMBER
CALLBACK_URI = Config.CALLBACK_URI
COGNITIVE_SERVICES_ENDPOINT = Config.COGNITIVE_SERVICES_ENDPOINT

# Initialize variables
acs_client = None
call_connection = None
call_connection_id = None
server_call_id = None
room_id = None

# Global variables to store room and user details
room_details = None 

# Initialize ACS Client
async def create_acs_client():
    global acs_client
    acs_client = CallAutomationClient.from_connection_string(CONNECTION_STRING)
    print("Initialized ACS Client.")

# Create Room
async def create_room():
    identity_client = CommunicationIdentityClient.from_connection_string(CONNECTION_STRING)
    app.logger.info("Test")
    # Correct unpacking of the returned tuple
    user1, token1 = identity_client.create_user_and_token(["voip"])
    user2, token2 = identity_client.create_user_and_token(["voip"])
    
    communication_user_id1 = user1.properties['id']
    communication_user_id2 = user2.properties['id']
    # Now you can access the 'user' and 'token' separately
    print(f"Presenter: {communication_user_id1}, Token: {token1.token}")
    print(f"Attendee: {communication_user_id2}, Token: {token2.token}")

    rooms_client = RoomsClient.from_connection_string(CONNECTION_STRING)

    valid_from = datetime.now(timezone.utc)
    valid_until = valid_from + timedelta(weeks=7)
    # Create participants
    participants = [
        RoomParticipant(
            communication_identifier=CommunicationUserIdentifier(communication_user_id1),
            role=ParticipantRole.PRESENTER  # Presenter role
        ),
        RoomParticipant(
            communication_identifier=CommunicationUserIdentifier(communication_user_id2),
            role=ParticipantRole.CONSUMER  # Attendee role
        )
    ]
    
    try:
        create_room_response = rooms_client.create_room(
        valid_from=valid_from,
        valid_until=valid_until,
        participants=participants,
        pstn_dial_out_enabled=True
    )
    except HttpResponseError as ex:
        print(ex)
    
    global room_id
    room_id = create_room_response.id
    print(f"Room created with ID: {room_id}")
    
    room_details = {
        "room_id": create_room_response.id,
        "presenter_id": communication_user_id1,
        "presenter_token": token1.token,
        "attendee_id": communication_user_id2,
        "attendee_token": token2.token
    }
    return room_details
# Connect call to the room
async def connect_call():
    global call_connection_id
    if room_id:
# Use CALLBACK_URI from the config
        callback_uri = CALLBACK_URI + "/api/callbacks"
        app.logger.info(f"Callback URL: {callback_uri}")
        app.logger.info(f"Room ID: {room_id}")
        
        response = await acs_client.connect_call(
        room_id=room_id,
        callback_url=callback_uri,
        cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT,
        operation_context="connectCallContext")
        print("Call connection initiated.")
        app.logger.info(f"Connect request correlation id: {response.correlation_id}")
    else:
        print("Room ID is empty or room not available.")

# Add PSTN participant to the call
async def add_pstn_participant():
    if call_connection_id:
        target = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
        source_caller_id_number = PhoneNumberIdentifier(ACS_RESOURCE_PHONE_NUMBER)
        app.logger.info("source_caller_id_number: %s", source_caller_id_number)
        
        add_participant_result= await call_connection.add_participant(target_participant=target, 
                                                                        source_caller_id_number=source_caller_id_number, 
                                                                        operation_context=None,
                                                                        invitation_timeout=15)
        app.logger.info("Add Translator to the call: %s", add_participant_result.invitation_id)
                    
        print(f"Adding PSTN participant with invitation ID: {add_participant_result.invitation_id}")
    else:
        print("Call connection ID is empty or call not active.")

# Hangup the call
async def hang_up_call():
    if call_connection:
        await call_connection.hang_up(True)
        print("Call hung up.")
        
async def handle_play():
    play_source = TextSource(text="Hello, welcome to connect room contoso app.", voice_name="en-US-NancyNeural")
    if call_connection:
        await call_connection.play_media_to_all(play_source)
        
# Routes
@app.route('/')
async def home():
    global room_details
# Check if room details already exist
    if not room_details:
        # Create the ACS client and room only if room is not created yet
        await create_acs_client()
        room_details = await create_room()
    
    # Render the page with the room details
    return await render_template('index.html', details=room_details)

@app.route('/connectCall', methods=['GET'])
async def connect_call_route():
    await connect_call()
    return redirect('/')

@app.route('/addParticipant', methods=['GET'])
async def add_participant_route():
    await add_pstn_participant()
    return redirect('/')

@app.route('/hangup', methods=['GET'])
async def hangup_route():
    await hang_up_call()
    return redirect('/')

@app.route('/playMedia', methods=['GET'])
async def play_media_route():
    await handle_play()
    return redirect('/')

@app.route('/api/callbacks', methods=['POST'])
async def handle_callbacks():
    try:
        global call_connection_id, server_call_id, call_connection

        # Extract the first event from the request body
        events = await request.json
        event = events[0]  # Assumes at least one event is present
        event_data = event['data']
        # Handle specific event types
        if event['type'] == "Microsoft.Communication.CallConnected":
            app.logger.info("Received CallConnected event")
            app.logger.info(f"Correlation ID: {event_data['correlationId']}")
             # Extract necessary details
            call_connection_id = event_data['callConnectionId']
            server_call_id = event_data['serverCallId']
            call_connection = acs_client.get_call_connection(call_connection_id)

        elif event['type'] == "Microsoft.Communication.AddParticipantSucceeded":
            app.logger.info("Received AddParticipantSucceeded event")
            
        elif event['type'] == "Microsoft.Communication.AddParticipantFailed":
            result_info = event_data['resultInformation']
            app.logger.info("Received AddParticipantFailed event")
            app.logger.info(f"Code: {result_info['code']}, Subcode: {result_info['subCode']}")
            app.logger.info(f"Message: {result_info['message']}")
        elif event['type'] == "Microsoft.Communication.PlayCompleted":
             app.logger.info("Received PlayCompleted event")
        elif event['type'] == "Microsoft.Communication.PlayFailed":
            result_info = event_data['resultInformation']
            app.logger.info("Received PlayFailed event")
            app.logger.info(f"Code: {result_info['code']}, Subcode: {result_info['subCode']}")
            app.logger.info(f"Message: {result_info['message']}")
        elif event['type'] == "Microsoft.Communication.CallDisconnected":
            app.logger.info("Received CallDisconnected event")
            app.logger.info(f"Correlation ID: {event_data['correlationId']}")

        # Respond with a success status
        return jsonify({"status": "OK"}), 200

    except Exception as e:
        app.logger.error(f"Error processing callback: {e}")
        return jsonify({"error": "Internal server error"}), 500
    
if __name__ == '__main__':
    app.logger.setLevel(INFO)
    app.run(port=PORT)

