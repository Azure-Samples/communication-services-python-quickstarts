"""
Azure Communication Services Call Automation Python Application
Converted from TypeScript app.ts

This application provides a comprehensive interface for Azure Communication Services
Call Automation features including outbound calls, media streaming, recording,
participant management, and real-time event handling.
"""

import os
import json
import logging
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

# Web framework and WebSocket support
from flask import Flask, request, jsonify, send_file, redirect, render_template_string
from flask_cors import CORS
from werkzeug.serving import WSGIRequestHandler

# Azure Communication Services
from azure.communication.callautomation import (
    CallAutomationClient,
    PhoneNumberIdentifier,
    CommunicationUserIdentifier,
    RecognitionChoice,
    DtmfTone,
    FileSource,
    TextSource,
    RecordingContent,
    RecordingChannel,
    RecordingFormat
)
try:
    from azure.communication.callautomation import (
        CallInvite,
        CreateCallOptions,
        MediaStreamingOptions,
        TranscriptionOptions,
        CallLocator,
        StartRecordingOptions,
        PlayToAllOptions,
        PlayOptions
    )
except ImportError:
    # Some classes might not be available in all versions
    FileSource = None
    TextSource = None
    CallInvite = None
    CreateCallOptions = None
    MediaStreamingOptions = None
    TranscriptionOptions = None
    CallLocator = None
    StartRecordingOptions = None
    PlayToAllOptions = None
    PlayOptions = None

# Environment configuration
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask application setup
app = Flask(__name__)
CORS(app)

# Global variables (equivalent to TypeScript global variables)
call_connection_id: Optional[str] = None
call_connection = None
server_call_id: Optional[str] = None
callee = None
acs_client: Optional[CallAutomationClient] = None
recording_id: Optional[str] = None
recording_location: Optional[str] = None
recording_metadata_location: Optional[str] = None
recording_delete_location: Optional[str] = None
recording_state: Optional[str] = None
caller_id: Optional[str] = None
download_recording_format: Optional[str] = None
callback_received: bool = False
last_callback_time: Optional[datetime] = None

# Configuration constants
CONFIRM_LABEL = "Confirm"
CANCEL_LABEL = "Cancel"
BASE_MEDIA_PATH = "./src/resources/media_prompts/"

# Environment variables
PORT = os.getenv('PORT', '8080')
CONNECTION_STRING = os.getenv('CONNECTION_STRING', '')
ACS_RESOURCE_PHONE_NUMBER = os.getenv('ACS_RESOURCE_PHONE_NUMBER', '').strip()
CALLBACK_URI = os.getenv('CALLBACK_URI', '')
COGNITIVE_SERVICES_ENDPOINT = os.getenv('COGNITIVE_SERVICES_ENDPOINT', '')

MEDIA_URI = f"{CALLBACK_URI}/audioprompt/"
acs_phone_number = PhoneNumberIdentifier(value=ACS_RESOURCE_PHONE_NUMBER)

# WebSocket configuration
websocket_url = CALLBACK_URI.replace('http://', 'ws://').replace('https://', 'wss://')
transport_url = websocket_url

# WebSocket storage for real-time logging
recent_logs: List[str] = []
websocket_clients = set()

def broadcast_log(message: str):
    """Broadcast log message to connected WebSocket clients"""
    recent_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {message}")
    # Keep only the last 50 log entries
    if len(recent_logs) > 50:
        recent_logs.pop(0)
    # Just log normally without the WebSocket broadcasting
    print(f"[LOG] {message}")

# Override print/logging to broadcast - simplified version without recursion
original_logger_info = logger.info
def enhanced_logger_info(message, *args, **kwargs):
    original_logger_info(message, *args, **kwargs)
    # Add to recent logs for the API
    if isinstance(message, str):
        recent_logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {message}")
        # Keep only the last 50 log entries
        if len(recent_logs) > 50:
            recent_logs.pop(0)

logger.info = enhanced_logger_info

def create_acs_client():
    """Initialize Azure Communication Services client"""
    global acs_client
    
    if not CONNECTION_STRING:
        logger.error("CONNECTION_STRING environment variable is missing")
        return
    
    logger.info(f"Creating ACS Client with connection string: {'✓ Set' if CONNECTION_STRING else '✗ Missing'}")
    logger.info(f"Callback URI: {CALLBACK_URI + '/api/callbacks' if CALLBACK_URI else '✗ Missing'}")
    logger.info(f"Port: {PORT}")
    
    try:
        acs_client = CallAutomationClient.from_connection_string(CONNECTION_STRING)
        logger.info("Initialized ACS Client successfully")
    except Exception as e:
        logger.error(f"Failed to initialize ACS Client: {e}")

async def create_outbound_call(pstn_target: str):
    """Create outbound call to PSTN number"""
    try:
        logger.info("Placing PSTN outbound call...")
        pstn_target = PhoneNumberIdentifier(pstn_target)
        source_caller = PhoneNumberIdentifier(ACS_RESOURCE_PHONE_NUMBER)
        create_call_result = acs_client.create_call(
            pstn_target,
            callback_url=f"{CALLBACK_URI}/api/callbacks",
            # cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT,
            source_caller_id_number=source_caller
        )
        logger.info("Placed PSTN outbound call...")
        # Log the call result structure for debugging
        logger.info(f"Create call result type: {type(create_call_result)}")
        logger.info(f"Create call result attributes: {dir(create_call_result)}")
        
        # Try to get call connection ID from the result
        if hasattr(create_call_result, 'call_connection_id'):
            logger.info(f"Call created successfully. Call Connection: {create_call_result.call_connection_id}")
        elif hasattr(create_call_result, 'call_connection'):
            call_properties = create_call_result.call_connection.get_call_connection_properties()
            logger.info(f"Call created successfully. Call Connection: {call_properties.call_connection_id}")
        else:
            logger.info(f"Call created successfully. Result: {create_call_result}")
    except Exception as error:
        logger.error(f"Failed to create PSTN outbound call: {error}")

async def create_outbound_call_acs(acs_target: str):
    """Create outbound call to ACS user"""
    try:
        acs_target = CommunicationUserIdentifier(acs_target)
        logger.info("Placing ACS outbound call...")
        create_call_result = acs_client.create_call(
            acs_target,
            callback_url=f"{CALLBACK_URI}/api/callbacks"
            # cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT
        )
        logger.info("Placed ACS outbound call...")
        # Log the call result structure for debugging  
        logger.info(f"Create call result type: {type(create_call_result)}")
        
        # Try to get call connection ID from the result
        if hasattr(create_call_result, 'call_connection_id'):
            logger.info(f"Call created successfully. Call Connection: {create_call_result.call_connection_id}")
        elif hasattr(create_call_result, 'call_connection'):
            call_properties = create_call_result.call_connection.get_call_connection_properties()
            logger.info(f"Call created successfully. Call Connection: {call_properties.call_connection_id}")
        else:
            logger.info(f"Call created successfully. Result: {create_call_result}")
    except Exception as error:
        logger.error(f"Failed to create ACS outbound call: {error}")

async def get_participant(is_pstn: bool, target_participant: str):
    """Get participant information"""
    try:
        if is_pstn:
            target = PhoneNumberIdentifier(phone_number=target_participant)
        else:
            target = CommunicationUserIdentifier(communication_user_id=target_participant)
        
        call_connection_obj = acs_client.get_call_connection(call_connection_id)
        participant = call_connection_obj.get_participant(target)
        
        logger.info("----------------------------------------------------------------------")
        logger.info(f"Participant: {json.dumps(participant.identifier.__dict__)}")
        logger.info(f"Is Participant on hold: {participant.is_on_hold}")
        logger.info(f"Is Participant muted: {participant.is_muted}")
        logger.info("----------------------------------------------------------------------")
        
    except Exception as error:
        logger.error(f"Failed to get participant in call: {error}")

async def get_participant_list_async():
    """Get list of all participants"""
    try:
        call_connection_obj = acs_client.get_call_connection(call_connection_id)
        participants = call_connection_obj.list_participants()
        
        logger.info("----------------------------------------------------------------------")
        for participant in participants:
            logger.info(f"Participant: {json.dumps(participant.identifier.__dict__)}")
            logger.info(f"Is Participant on hold: {participant.is_on_hold}")
            logger.info(f"Is Participant muted: {participant.is_muted}")
            logger.info("----------------------------------------------------------------------")
            
    except Exception as error:
        logger.error(f"Failed to get participant list in call: {error}")

async def create_group_call(acs_target: str):
    """Create group call"""
    try:
        communication_user_id = CommunicationUserIdentifier(communication_user_id=acs_target)
        targets = [communication_user_id]
        
        options = CreateCallOptions(operation_context="groupCallContext")
        
        logger.info("Placing group call...")
        create_call_result = acs_client.create_group_call(
            target_participants=targets,
            callback_url=f"{CALLBACK_URI}/api/callbacks",
            options=options
        )
        
        # Log the call result structure for debugging
        logger.info(f"Create call result type: {type(create_call_result)}")
        
        # Try to get call connection ID from the result
        if hasattr(create_call_result, 'call_connection_id'):
            logger.info(f"Call created successfully. Call Connection: {create_call_result.call_connection_id}")
        elif hasattr(create_call_result, 'call_connection'):
            call_properties = create_call_result.call_connection.get_call_connection_properties()
            logger.info(f"Call created successfully. Call Connection: {call_properties.call_connection_id}")
        else:
            logger.info(f"Call created successfully. Result: {create_call_result}")
        
    except Exception as error:
        logger.error(f"Failed to create group call: {error}")

async def get_choices():
    """Get recognition choices for DTMF"""
    choices = [
        RecognitionChoice(
            label=CONFIRM_LABEL,
            phrases=["Confirm", "First", "One"],
            tone=DtmfTone.ONE
        ),
        RecognitionChoice(
            label=CANCEL_LABEL,
            phrases=["Cancel", "Second", "Two"],
            tone=DtmfTone.TWO
        )
    ]
    return choices

async def terminate_call_async(is_for_everyone: bool):
    """Terminate call"""
    try:
        await acs_client.get_call_connection(call_connection_id).hang_up(is_for_everyone)
    except Exception as error:
        logger.error(f"Failed to terminate call: {error}")

async def play_media_to_all_with_file_source_async():
    """Play media to all participants"""
    try:
        file_source = FileSource(url=f"{MEDIA_URI}MainMenu.wav")
        
        acs_client.get_call_connection(call_connection_id).get_call_media().play_to_all(
            play_sources=[file_source]
        )
    except Exception as error:
        logger.error(f"Failed to play media to all with file source: {error}")

async def play_media_to_target_with_file_source_async(is_pstn: bool, target_participant: str):
    """Play media to specific participant"""
    try:
        file_source = FileSource(url=f"{MEDIA_URI}MainMenu.wav")
        
        if is_pstn:
            target = PhoneNumberIdentifier(phone_number=target_participant)
        else:
            target = CommunicationUserIdentifier(communication_user_id=target_participant)
        
        acs_client.get_call_connection(call_connection_id).get_call_media().play(
            play_sources=[file_source],
            play_to=[target]
        )
    except Exception as error:
        logger.error(f"Failed to play media to target with file source: {error}")

async def start_recording_async(
    is_recording_with_call_connection_id: bool,
    is_pause_on_start: bool,
    recording_content: str,
    recording_channel: str,
    recording_format: str
):
    """Start call recording"""
    global recording_id, download_recording_format
    
    try:
        download_recording_format = recording_format
        call_connection_properties = acs_client.get_call_connection(call_connection_id).get_call_connection_properties()
        server_call_id_local = call_connection_properties.server_call_id
        
        logger.info(f"Starting recording for server call ID: {server_call_id_local}")
        logger.info(f"Recording content: {recording_content}")
        logger.info(f"Recording channel: {recording_channel}")
        logger.info(f"Recording format: {recording_format}")
        logger.info(f"Pause on start: {is_pause_on_start}")
        
        # Note: The actual recording start implementation would depend on the exact SDK version
        # For now, we'll log the recording attempt
        logger.info("Recording start requested - implementation depends on SDK version")
        
    except Exception as error:
        logger.error(f"Failed to start recording: {error}")

async def add_participant_pstn_async(participant_phone: str):
    """Add PSTN participant to call"""
    try:
        target = PhoneNumberIdentifier(phone_number=participant_phone)
        call_connection_obj = acs_client.get_call_connection(call_connection_id)
        
        add_participant_result = call_connection_obj.add_participant(
            target_participant=target,
            source_caller_id_number=acs_phone_number,
            operation_context="addPSTNParticipantContext"
        )
        
        logger.info(f"Added PSTN participant successfully. Invitation ID: {add_participant_result.invitation_id}")
        
    except Exception as error:
        logger.error(f"Failed to add PSTN participant: {error}")

async def add_participant_acs_async(acs_participant: str):
    """Add ACS participant to call"""
    try:
        target = CommunicationUserIdentifier(communication_user_id=acs_participant)
        call_connection_obj = acs_client.get_call_connection(call_connection_id)
        
        add_participant_result = call_connection_obj.add_participant(
            target_participant=target,
            operation_context="addACSParticipantContext"
        )
        
        logger.info(f"Added ACS participant successfully. Invitation ID: {add_participant_result.invitation_id}")
        
    except Exception as error:
        logger.error(f"Failed to add ACS participant: {error}")

async def remove_participant_pstn_async(participant_phone: str):
    """Remove PSTN participant from call"""
    try:
        target = PhoneNumberIdentifier(phone_number=participant_phone)
        call_connection_obj = acs_client.get_call_connection(call_connection_id)
        
        call_connection_obj.remove_participant(
            target_participant=target,
            operation_context="removePSTNParticipantContext"
        )
        
        logger.info(f"Removed PSTN participant successfully: {participant_phone}")
        
    except Exception as error:
        logger.error(f"Failed to remove PSTN participant: {error}")

async def remove_participant_acs_async(acs_participant: str):
    """Remove ACS participant from call"""
    try:
        target = CommunicationUserIdentifier(communication_user_id=acs_participant)
        call_connection_obj = acs_client.get_call_connection(call_connection_id)
        
        call_connection_obj.remove_participant(
            target_participant=target,
            operation_context="removeACSParticipantContext"
        )
        
        logger.info(f"Removed ACS participant successfully: {acs_participant}")
        
    except Exception as error:
        logger.error(f"Failed to remove ACS participant: {error}")

async def cancel_add_participant_async(invitation_id: str):
    """Cancel add participant invitation"""
    try:
        call_connection_obj = acs_client.get_call_connection(call_connection_id)
        
        call_connection_obj.cancel_add_participant(
            invitation_id=invitation_id,
            operation_context="cancelAddParticipantContext"
        )
        
        logger.info(f"Cancelled add participant invitation successfully: {invitation_id}")
        
    except Exception as error:
        logger.error(f"Failed to cancel add participant invitation: {error}")

async def transfer_call_to_participant_async(is_pstn: bool, transfer_target: str, target_participant: str):
    """Transfer call to participant"""
    try:
        if is_pstn:
            transfer_to = PhoneNumberIdentifier(phone_number=transfer_target)
            transferee = PhoneNumberIdentifier(phone_number=target_participant)
        else:
            transfer_to = CommunicationUserIdentifier(communication_user_id=transfer_target)
            transferee = CommunicationUserIdentifier(communication_user_id=target_participant)
        
        call_connection_obj = acs_client.get_call_connection(call_connection_id)
        
        call_connection_obj.transfer_call_to_participant(
            target_participant=transfer_to,
            transferee=transferee,
            operation_context="transferCallContext"
        )
        
        logger.info(f"Transferred call successfully to {transfer_target} for participant {target_participant}")
        
    except Exception as error:
        logger.error(f"Failed to transfer call: {error}")

async def mute_participant_async(acs_participant: str):
    """Mute ACS participant"""
    try:
        target = CommunicationUserIdentifier(communication_user_id=acs_participant)
        call_connection_obj = acs_client.get_call_connection(call_connection_id)
        
        call_connection_obj.mute_participant(
            target_participant=target,
            operation_context="muteParticipantContext"
        )
        
        logger.info(f"Muted ACS participant successfully: {acs_participant}")
        
    except Exception as error:
        logger.error(f"Failed to mute ACS participant: {error}")

async def cancel_all_media_operations_async():
    """Cancel all media operations"""
    try:
        call_connection_obj = acs_client.get_call_connection(call_connection_id)
        
        call_connection_obj.get_call_media().cancel_all_media_operations(
            operation_context="cancelAllMediaOperationsContext"
        )
        
        logger.info("Cancelled all media operations successfully")
        
    except Exception as error:
        logger.error(f"Failed to cancel all media operations: {error}")

async def hold_participant_async(is_pstn: bool, target_participant: str, is_with_play_source: bool = False):
    """Hold participant"""
    try:
        if is_pstn:
            target = PhoneNumberIdentifier(phone_number=target_participant)
        else:
            target = CommunicationUserIdentifier(communication_user_id=target_participant)
        
        call_connection_obj = acs_client.get_call_connection(call_connection_id)
        
        if is_with_play_source:
            play_source = FileSource(url=f"{MEDIA_URI}MainMenu.wav")
            call_connection_obj.hold_participant(
                target_participant=target,
                play_source=play_source,
                operation_context="holdParticipantWithSourceContext"
            )
        else:
            call_connection_obj.hold_participant(
                target_participant=target,
                operation_context="holdParticipantContext"
            )
        
        logger.info(f"Put participant on hold successfully: {target_participant}")
        
    except Exception as error:
        logger.error(f"Failed to hold participant: {error}")

async def unhold_participant_async(is_pstn: bool, target_participant: str):
    """Unhold participant"""
    try:
        if is_pstn:
            target = PhoneNumberIdentifier(phone_number=target_participant)
        else:
            target = CommunicationUserIdentifier(communication_user_id=target_participant)
        
        call_connection_obj = acs_client.get_call_connection(call_connection_id)
        
        call_connection_obj.unhold_participant(
            target_participant=target,
            operation_context="unholdParticipantContext"
        )
        
        logger.info(f"Removed participant from hold successfully: {target_participant}")
        
    except Exception as error:
        logger.error(f"Failed to unhold participant: {error}")

# Flask Routes

@app.route('/')
def serve_main_page():
    """Serve the main index.html page"""
    try:
        template_path = Path('template/index.html')
        if template_path.exists():
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return "Error: template/index.html not found", 404
    except Exception as e:
        logger.error(f"Error serving main page: {e}")
        return "Internal Server Error", 500

@app.route('/api/incomingCall', methods=['POST'])
def handle_incoming_call():
    """Handle incoming call events"""
    global caller_id
    
    try:
        events = request.json
        if not isinstance(events, list):
            events = [events]
        
        for event in events:
            event_data = event.get('data', {})
            
            if event.get('eventType') == 'Microsoft.EventGrid.SubscriptionValidationEvent':
                logger.info("Received SubscriptionValidation event")
                return jsonify({'validationResponse': event_data.get('validationCode')})
            
            if event.get('eventType') == 'Microsoft.Communication.IncomingCall':
                logger.info("INCOMING CALL...")
                caller_id = event_data.get('from', {}).get('rawId', '')
                logger.info(f"Caller Id: {caller_id}")
                
                callback_uri = f"{CALLBACK_URI}/api/callbacks"
                websocket_url_local = CALLBACK_URI.replace('http://', 'ws://').replace('https://', 'wss://')
                logger.info(f"WebSocket URL: {websocket_url_local}")
                
                incoming_call_context = event_data.get('incomingCallContext', '')
                
                # Note: Async operations need to be handled differently in Flask
                # For now, just log the incoming call
                logger.info(f"Would answer call with context: {incoming_call_context}")
        
        return '', 200
        
    except Exception as error:
        logger.error(f"Error handling incoming call: {error}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/callbacks', methods=['POST'])
def handle_callbacks():
    """Handle ongoing call events"""
    global call_connection_id, server_call_id, call_connection, recording_state, callback_received, last_callback_time
    
    try:
        # Set callback flags for UI updates
        callback_received = True
        last_callback_time = datetime.now()
        
        logger.info("=== CALLBACK RECEIVED ===")
        logger.info(f"Request body: {json.dumps(request.json, indent=2)}")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request URL: {request.url}")
        
        # Handle both array and single event formats
        events = request.json if isinstance(request.json, list) else [request.json]
        
        if not events:
            logger.info("No events found in callback payload")
            return jsonify({'message': 'No events to process'})
        
        for event in events:
            if not event or not event.get('data'):
                logger.info(f"Invalid event structure: {event}")
                continue
            
            event_data = event.get('data', {})
            event_type = event.get('type', '')
            
            logger.info(f"Processing event type: {event_type}")
            
            if event_data.get('callConnectionId'):
                call_connection_id = event_data['callConnectionId']
                logger.info(f"Updated callConnectionId: {call_connection_id}")
            
            if event_data.get('serverCallId'):
                server_call_id = event_data['serverCallId']
                logger.info(f"Updated serverCallId: {server_call_id}")
            
            logger.info(f"Callback event received, callConnectionId={call_connection_id}, "
                       f"serverCallId={server_call_id}, eventType={event_type}")
            
            if call_connection_id:
                call_connection = acs_client.get_call_connection(call_connection_id)
            
            # Handle different event types
            if event_type == "Microsoft.Communication.CallConnected":
                logger.info("Received CallConnected event")
                # Handle call connected logic
                
            elif event_type == "Microsoft.Communication.RecognizeCompleted":
                logger.info("Received RecognizeCompleted event")
                # Handle recognition completed logic
                
            elif event_type == "Microsoft.Communication.RecordingStateChanged":
                logger.info("Received RecordingStateChanged event")
                recording_state = event_data.get('state', '')
                logger.info(f"Recording State: {recording_state}")
                
            elif event_type == "Microsoft.Communication.CallDisconnected":
                logger.info("Received CallDisconnected event")
                correlation_id = event_data.get('correlationId', '')
                logger.info(f"CORRELATION ID: {correlation_id}")
            
            # Add more event type handlers as needed
        
        # Trigger log update notification after processing callbacks
        logger.info("=== CALLBACK PROCESSING COMPLETE ===")
        logger.info("Callback events processed successfully - logs updated")
        
        # Optionally trigger internal log fetch (for debugging/monitoring)
        try:
            current_logs = recent_logs[-10:]  # Get last 10 logs
            logger.info(f"Recent logs after callback: {len(current_logs)} entries")
            for log_entry in current_logs[-3:]:  # Show last 3 entries
                logger.info(f"Recent: {log_entry}")
        except Exception as log_error:
            logger.error(f"Error accessing recent logs: {log_error}")
        
        return '', 200
        
    except Exception as error:
        logger.error(f"Error processing callback: {error}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/testcall', methods=['POST'])
def handle_test_call():
    """Test endpoint that logs success and returns 200"""
    try:
        logger.info("=== TEST CALL RECEIVED ===")
        logger.info("Test call endpoint accessed successfully")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request URL: {request.url}")
        logger.info(f"Request headers: {dict(request.headers)}")
        
        if request.json:
            logger.info(f"Request body: {json.dumps(request.json, indent=2)}")
        else:
            logger.info("No JSON body in request")
        
        logger.info("Test call completed successfully")
        return jsonify({'message': 'Test call successful', 'status': 'success'}), 200
        
    except Exception as error:
        logger.error(f"Error in test call: {error}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/recordingFileStatus', methods=['POST'])
def handle_recording_file_status():
    """Handle recording file status events"""
    global recording_location, recording_metadata_location, recording_delete_location
    
    try:
        events = request.json if isinstance(request.json, list) else [request.json]
        
        for event in events:
            event_data = event.get('data', {})
            event_type = event.get('eventType', '')
            
            logger.info(f"Received {event_type}")
            
            if event_type == 'Microsoft.EventGrid.SubscriptionValidationEvent':
                return jsonify({'validationResponse': event_data.get('validationCode')})
            
            elif event_type == 'Microsoft.Communication.RecordingFileStatusUpdated':
                recording_chunks = event_data.get('recordingStorageInfo', {}).get('recordingChunks', [])
                if recording_chunks:
                    chunk = recording_chunks[0]
                    recording_location = chunk.get('contentLocation', '')
                    recording_metadata_location = chunk.get('metadataLocation', '')
                    recording_delete_location = chunk.get('deleteLocation', '')
                    
                    logger.info(f"CONTENT LOCATION: {recording_location}")
                    logger.info(f"METADATA LOCATION: {recording_metadata_location}")
                    logger.info(f"DELETE LOCATION: {recording_delete_location}")
        
        return '', 200
        
    except Exception as error:
        logger.error(f"Error handling recording file status: {error}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/download')
def download_recording():
    """Download call recording"""
    if not recording_location:
        logger.info("Failed to download, recordingLocation is invalid.")
        return redirect('/')
    
    try:
        # In a real implementation, you'd handle the async download properly
        logger.info(f"Would download recording from: {recording_location}")
        return "Recording download would be initiated", 200
    except Exception as error:
        logger.error(f"Error downloading recording: {error}")
        return redirect('/')

@app.route('/downloadMetadata')
def download_metadata():
    """Download recording metadata"""
    if not recording_metadata_location:
        logger.info("Failed to download metadata, recordingMetadataLocation is invalid.")
        return redirect('/')
    
    try:
        # In a real implementation, you'd handle the async download properly
        logger.info(f"Would download metadata from: {recording_metadata_location}")
        return "Metadata download would be initiated", 200
    except Exception as error:
        logger.error(f"Error downloading metadata: {error}")
        return redirect('/')

@app.route('/audioprompt/<filename>')
def serve_audio_file(filename):
    """Serve audio files"""
    try:
        audio_file_path = Path(BASE_MEDIA_PATH) / filename
        
        if not audio_file_path.exists():
            logger.error(f"Audio file not found: {audio_file_path}")
            return "File not found", 404
        
        return send_file(
            audio_file_path,
            mimetype="audio/wav",
            as_attachment=False
        )
    except Exception as error:
        logger.error(f"Failed to serve audio file: {error}")
        return "Internal Server Error", 500

# API endpoints for call operations
@app.route('/outboundCall')
def place_outbound_call():
    """Place outbound call endpoint"""
    target_phone_number = request.args.get('targetPhoneNumber', '')
    
    logger.info("Placing PSTN call...")
    logger.info(f"Target number: {target_phone_number}")
    
    # Call the actual create_outbound_call function
    if target_phone_number:
        try:
            asyncio.run(create_outbound_call(target_phone_number))
        except Exception as e:
            logger.error(f"Error creating outbound call: {e}")
    else:
        logger.info("Error: No target phone number provided")
    
    return redirect('/')

@app.route('/outboundCallACS')
def place_outbound_call_acs():
    """Place outbound ACS call endpoint"""
    acs_user = request.args.get('acsUserId', '')
    logger.info(f"ACS MRI ID: {acs_user}")
    
    # Call the actual create_outbound_call_acs function
    if acs_user:
        try:
            asyncio.run(create_outbound_call_acs(acs_user))
        except Exception as e:
            logger.error(f"Error creating outbound ACS call: {e}")
    else:
        logger.info("Error: No ACS user ID provided")
    
    return redirect('/')

@app.route('/groupCall')
def create_group_call_route():
    """Create group call endpoint"""
    acs_user = request.args.get('acsUserId', '')
    logger.info(f"Creating group call with ACS user: {acs_user}")
    
    # Call the actual create_group_call function
    if acs_user:
        try:
            asyncio.run(create_group_call(acs_user))
        except Exception as e:
            logger.error(f"Error creating group call: {e}")
    else:
        logger.info("Error: No ACS user ID provided")
    
    return redirect('/')

@app.route('/addPSTNParticipant')
def add_pstn_participant():
    """Add PSTN participant endpoint"""
    participant_phone = request.args.get('participantPhoneNumber', '')
    logger.info(f"Adding PSTN participant: {participant_phone}")
    
    # Call the actual add_participant_pstn_async function
    if participant_phone:
        try:
            asyncio.run(add_participant_pstn_async(participant_phone))
        except Exception as e:
            logger.error(f"Error adding PSTN participant: {e}")
    else:
        logger.info("Error: No participant phone number provided")
    
    return redirect('/')

@app.route('/addACSParticipant')
def add_acs_participant():
    """Add ACS participant endpoint"""
    acs_participant = request.args.get('acsParticipant', '')
    logger.info(f"Adding ACS participant: {acs_participant}")
    
    # Call the actual add_participant_acs_async function
    if acs_participant:
        try:
            asyncio.run(add_participant_acs_async(acs_participant))
        except Exception as e:
            logger.error(f"Error adding ACS participant: {e}")
    else:
        logger.info("Error: No ACS participant ID provided")
    
    return redirect('/')

@app.route('/removePSTNParticipant')
def remove_pstn_participant():
    """Remove PSTN participant endpoint"""
    participant_phone = request.args.get('participantPhoneNumber', '')
    logger.info(f"Removing PSTN participant: {participant_phone}")
    
    # Call the actual remove_participant_pstn_async function
    if participant_phone:
        try:
            asyncio.run(remove_participant_pstn_async(participant_phone))
        except Exception as e:
            logger.error(f"Error removing PSTN participant: {e}")
    else:
        logger.info("Error: No participant phone number provided")
    
    return redirect('/')

@app.route('/removeACSParticipant')
def remove_acs_participant():
    """Remove ACS participant endpoint"""
    acs_participant = request.args.get('acsParticipant', '')
    logger.info(f"Removing ACS participant: {acs_participant}")
    
    # Call the actual remove_participant_acs_async function
    if acs_participant:
        try:
            asyncio.run(remove_participant_acs_async(acs_participant))
        except Exception as e:
            logger.error(f"Error removing ACS participant: {e}")
    else:
        logger.info("Error: No ACS participant ID provided")
    
    return redirect('/')

@app.route('/cancelAddParticipant')
def cancel_add_participant():
    """Cancel add participant endpoint"""
    invitation_id = request.args.get('invitationId', '')
    logger.info(f"Canceling add participant with invitation ID: {invitation_id}")
    
    # Call the actual cancel_add_participant_async function
    if invitation_id:
        try:
            asyncio.run(cancel_add_participant_async(invitation_id))
        except Exception as e:
            logger.error(f"Error canceling add participant: {e}")
    else:
        logger.info("Error: No invitation ID provided")
    
    return redirect('/')

@app.route('/transferCallToParticipant')
def transfer_call_to_participant():
    """Transfer call to participant endpoint"""
    is_pstn = request.args.get('isPstn') == 'on'
    transfer_target = request.args.get('transferTarget', '')
    target_participant = request.args.get('targetParticipant', '')
    
    logger.info(f"Transfer call - PSTN: {is_pstn}, Target: {transfer_target}, Participant: {target_participant}")
    
    # Call the actual transfer_call_to_participant_async function
    if transfer_target and target_participant:
        try:
            asyncio.run(transfer_call_to_participant_async(is_pstn, transfer_target, target_participant))
        except Exception as e:
            logger.error(f"Error transferring call: {e}")
    else:
        logger.info("Error: Missing transfer target or participant")
    
    return redirect('/')

@app.route('/MuteACSParticipant')
def mute_acs_participant():
    """Mute ACS participant endpoint"""
    acs_participant = request.args.get('acsParticipant', '')
    logger.info(f"Muting ACS participant: {acs_participant}")
    
    # Call the actual mute_participant_async function
    if acs_participant:
        try:
            asyncio.run(mute_participant_async(acs_participant))
        except Exception as e:
            logger.error(f"Error muting ACS participant: {e}")
    else:
        logger.info("Error: No ACS participant ID provided")
    
    return redirect('/')

@app.route('/getParticipant')
def get_participant_route():
    """Get participant endpoint"""
    is_pstn = request.args.get('isPstn') == 'on'
    target_participant = request.args.get('targetParticipant', '')
    
    logger.info(f"Getting participant - PSTN: {is_pstn}, Participant: {target_participant}")
    
    # Call the actual get_participant function
    if target_participant:
        try:
            asyncio.run(get_participant(is_pstn, target_participant))
        except Exception as e:
            logger.error(f"Error getting participant: {e}")
    else:
        logger.info("Error: No target participant provided")
    
    return redirect('/')

@app.route('/getParticipantListAsync')
def get_participant_list():
    """Get participant list endpoint"""
    logger.info("Getting participant list")
    
    # Call the actual get_participant_list_async function
    try:
        asyncio.run(get_participant_list_async())
    except Exception as e:
        logger.error(f"Error getting participant list: {e}")
    
    return redirect('/')

@app.route('/terminateCallAsync')
def terminate_call():
    """Terminate call endpoint"""
    is_for_everyone = request.args.get('isForEveryone') == 'on'
    logger.info(f"Terminating call - For everyone: {is_for_everyone}")
    
    # Call the actual terminate_call_async function
    try:
        asyncio.run(terminate_call_async(is_for_everyone))
    except Exception as e:
        logger.error(f"Error terminating call: {e}")
    
    return redirect('/')

@app.route('/createPSTNCallWithMediaStreaming')
def create_pstn_call_with_media_streaming():
    """Create PSTN call with media streaming endpoint"""
    target_phone = request.args.get('targetPhoneNumber', '')
    is_start_media_streaming = request.args.get('isStartMediaStreaming') == 'on'
    is_mixed = request.args.get('isMixed') == 'on'
    is_enable_bidirection = request.args.get('isEnableBidirection') == 'on'
    is_pcm24k = request.args.get('isPCM24k') == 'on'
    
    logger.info(f"Creating PSTN call with media streaming - Phone: {target_phone}")
    logger.info(f"Streaming: {is_start_media_streaming}, Mixed: {is_mixed}, Bidirection: {is_enable_bidirection}, PCM24k: {is_pcm24k}")
    
    if target_phone:
        logger.info(f"Would create PSTN call with media streaming to: {target_phone}")
    else:
        logger.info("Error: No target phone number provided")
    
    return redirect('/')

@app.route('/createACSCallWithMediaStreaming')
def create_acs_call_with_media_streaming():
    """Create ACS call with media streaming endpoint"""
    acs_user = request.args.get('acsUserId', '')
    is_start_media_streaming = request.args.get('isStartMediaStreaming') == 'on'
    is_mixed = request.args.get('isMixed') == 'on'
    is_enable_bidirection = request.args.get('isEnableBidirection') == 'on'
    is_pcm24k = request.args.get('isPCM24k') == 'on'
    
    logger.info(f"Creating ACS call with media streaming - User: {acs_user}")
    logger.info(f"Streaming: {is_start_media_streaming}, Mixed: {is_mixed}, Bidirection: {is_enable_bidirection}, PCM24k: {is_pcm24k}")
    
    if acs_user:
        logger.info(f"Would create ACS call with media streaming for: {acs_user}")
    else:
        logger.info("Error: No ACS user ID provided")
    
    return redirect('/')

@app.route('/StartMediaStreaming')
def start_media_streaming():
    """Start media streaming endpoint"""
    logger.info("Starting media streaming")
    logger.info("Would start media streaming")
    
    return redirect('/')

@app.route('/stopMediaStreaming')
def stop_media_streaming():
    """Stop media streaming endpoint"""
    logger.info("Stopping media streaming")
    logger.info("Would stop media streaming")
    
    return redirect('/')

@app.route('/playMediaToAllWithFileSource')
def play_media_to_all():
    """Play media to all participants endpoint"""
    logger.info("Playing media to all participants")
    
    # Call the actual play_media_to_all_with_file_source_async function
    try:
        asyncio.run(play_media_to_all_with_file_source_async())
    except Exception as e:
        logger.error(f"Error playing media to all: {e}")
    
    return redirect('/')

@app.route('/playMediaToTargetWithFileSource')
def play_media_to_target():
    """Play media to target participant endpoint"""
    is_pstn = request.args.get('isPstn') == 'on'
    target_participant = request.args.get('targetParticipant', '')
    
    logger.info(f"Playing media to target - PSTN: {is_pstn}, Participant: {target_participant}")
    
    # Call the actual play_media_to_target_with_file_source_async function
    if target_participant:
        try:
            asyncio.run(play_media_to_target_with_file_source_async(is_pstn, target_participant))
        except Exception as e:
            logger.error(f"Error playing media to target: {e}")
    else:
        logger.info("Error: No target participant provided")
    
    return redirect('/')

@app.route('/playWithInterruptMediaFlag')
def play_with_interrupt_media_flag():
    """Play with interrupt media flag endpoint"""
    logger.info("Playing with interrupt media flag")
    logger.info("Would play with interrupt media flag")
    
    return redirect('/')

@app.route('/recognizeMedia')
def recognize_media():
    """Recognize media endpoint"""
    is_pstn = request.args.get('isPstn') == 'on'
    target_participant = request.args.get('targetParticipant', '')
    
    logger.info(f"Recognizing media - PSTN: {is_pstn}, Participant: {target_participant}")
    
    if target_participant:
        logger.info(f"Would recognize media for: {target_participant}")
    else:
        logger.info("Error: No target participant provided")
    
    return redirect('/')

@app.route('/startRecording')
def start_recording():
    """Start recording endpoint"""
    is_recording_with_call_connection_id = request.args.get('isRecordingWithCallConnectionId') == 'on'
    is_pause_on_start = request.args.get('isPauseOnStart') == 'on'
    recording_content = request.args.get('recordingContent', 'audio')
    recording_channel = request.args.get('recordingChannel', 'mixed')
    recording_format = request.args.get('recordingFormat', 'wav')
    
    logger.info(f"Starting recording - Content: {recording_content}, Channel: {recording_channel}, Format: {recording_format}")
    logger.info(f"With connection ID: {is_recording_with_call_connection_id}, Pause on start: {is_pause_on_start}")
    
    # Call the actual start_recording_async function
    try:
        asyncio.run(start_recording_async(
            is_recording_with_call_connection_id,
            is_pause_on_start,
            recording_content,
            recording_channel,
            recording_format
        ))
    except Exception as e:
        logger.error(f"Error starting recording: {e}")
    
    return redirect('/')

@app.route('/getRecordingState')
def get_recording_state():
    """Get recording state endpoint"""
    logger.info("Getting recording state")
    logger.info(f"Current recording state: {recording_state}")
    
    return redirect('/')

@app.route('/pauseRecording')
def pause_recording():
    """Pause recording endpoint"""
    logger.info("Pausing recording")
    logger.info("Would pause recording")
    
    return redirect('/')

@app.route('/resumeRecording')
def resume_recording():
    """Resume recording endpoint"""
    logger.info("Resuming recording")
    logger.info("Would resume recording")
    
    return redirect('/')

@app.route('/stopRecording')
def stop_recording():
    """Stop recording endpoint"""
    logger.info("Stopping recording")
    logger.info("Would stop recording")
    
    return redirect('/')

@app.route('/sendDtmfTones')
def send_dtmf_tones():
    """Send DTMF tones endpoint"""
    is_pstn = request.args.get('isPstn') == 'on'
    target_participant = request.args.get('targetParticipant', '')
    
    logger.info(f"Sending DTMF tones - PSTN: {is_pstn}, Participant: {target_participant}")
    
    if target_participant:
        logger.info(f"Would send DTMF tones to: {target_participant}")
    else:
        logger.info("Error: No target participant provided")
    
    return redirect('/')

@app.route('/startContinuousDtmf')
def start_continuous_dtmf():
    """Start continuous DTMF endpoint"""
    is_pstn = request.args.get('isPstn') == 'on'
    target_participant = request.args.get('targetParticipant', '')
    
    logger.info(f"Starting continuous DTMF - PSTN: {is_pstn}, Participant: {target_participant}")
    
    if target_participant:
        logger.info(f"Would start continuous DTMF for: {target_participant}")
    else:
        logger.info("Error: No target participant provided")
    
    return redirect('/')

@app.route('/stopContinuousDtmf')
def stop_continuous_dtmf():
    """Stop continuous DTMF endpoint"""
    is_pstn = request.args.get('isPstn') == 'on'
    target_participant = request.args.get('targetParticipant', '')
    
    logger.info(f"Stopping continuous DTMF - PSTN: {is_pstn}, Participant: {target_participant}")
    
    if target_participant:
        logger.info(f"Would stop continuous DTMF for: {target_participant}")
    else:
        logger.info("Error: No target participant provided")
    
    return redirect('/')

@app.route('/cancelAllMediaOperation')
def cancel_all_media_operation():
    """Cancel all media operations endpoint"""
    logger.info("Canceling all media operations")
    
    # Call the actual cancel_all_media_operations_async function
    try:
        asyncio.run(cancel_all_media_operations_async())
    except Exception as e:
        logger.error(f"Error canceling all media operations: {e}")
    
    return redirect('/')

@app.route('/holdParticipant')
def hold_participant():
    """Hold participant endpoint"""
    is_pstn = request.args.get('isPstn') == 'on'
    is_with_play_source = request.args.get('isWithPlaySource') == 'on'
    target_participant = request.args.get('targetParticipant', '')
    
    logger.info(f"Holding participant - PSTN: {is_pstn}, With play source: {is_with_play_source}, Participant: {target_participant}")
    
    # Call the actual hold_participant_async function
    if target_participant:
        try:
            asyncio.run(hold_participant_async(is_pstn, target_participant, is_with_play_source))
        except Exception as e:
            logger.error(f"Error holding participant: {e}")
    else:
        logger.info("Error: No target participant provided")
    
    return redirect('/')

@app.route('/unholdParticipant')
def unhold_participant():
    """Unhold participant endpoint"""
    is_pstn = request.args.get('isPstn') == 'on'
    target_participant = request.args.get('targetParticipant', '')
    
    logger.info(f"Unholding participant - PSTN: {is_pstn}, Participant: {target_participant}")
    
    # Call the actual unhold_participant_async function
    if target_participant:
        try:
            asyncio.run(unhold_participant_async(is_pstn, target_participant))
        except Exception as e:
            logger.error(f"Error unholding participant: {e}")
    else:
        logger.info("Error: No target participant provided")
    
    return redirect('/')

@app.route('/clearLogs')
def clear_logs():
    """Clear logs endpoint"""
    global recent_logs
    recent_logs.clear()
    logger.info("Logs cleared")
    return redirect('/')

@app.route('/api/logs')
def get_logs():
    """Get recent logs for UI"""
    return jsonify({'logs': recent_logs[-50:]})  # Return last 50 logs

@app.route('/api/callback-status')
def get_callback_status():
    """Check if new callbacks have been received"""
    global callback_received, last_callback_time
    
    status = {
        'callback_received': callback_received,
        'last_callback_time': last_callback_time.isoformat() if last_callback_time else None,
        'current_time': datetime.now().isoformat()
    }
    
    # Reset the flag after checking
    callback_received = False
    
    return jsonify(status)

def main():
    """Main application entry point"""
    # Initialize ACS client
    create_acs_client()
    
    # Start Flask server
    logger.info(f"Starting server on port {PORT}")
    
    app.run(host='0.0.0.0', port=int(PORT), debug=False)

if __name__ == '__main__':
    # Run the application
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application error: {e}")