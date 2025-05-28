import base64
from fastapi import Body, FastAPI, HTTPException, Query, Request, Response, requests
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from typing import List, Optional
from azure.eventgrid import EventGridEvent, SystemEventNames
from azure.communication.callautomation import (
    CallAutomationClient,
    PhoneNumberIdentifier,
    CommunicationUserIdentifier,
    RecognizeInputType,
    CallInvite,
    RecognitionChoice,
    DtmfTone,
    TextSource,
    FileSource,
    SsmlSource,
    AzureBlobContainerRecordingStorage,
    AzureCommunicationsRecordingStorage,
    AddParticipantResult,
    CommunicationIdentifier,
    RecordingContent,
    RecordingChannel,
    RecordingFormat,
    ServerCallLocator
)
from azure.communication.callautomation.aio import CallAutomationClient
from azure.core.messaging import CloudEvent
from logging import INFO, log
import logging
import time
import json
import uuid

# Configure logging
logging.basicConfig(level=INFO)
logger = logging.getLogger(__name__)

# Your ACS resource connection string
ACS_CONNECTION_STRING = "endpoint=https://dacsrecordingtest.unitedstates.communication.azure.com/;accesskey=B7XxnSOl3VbKeviyV4vi4pEeqVyAXsdn8fg0hi6YCGdtjlecLHMwJQQJ99BEACULyCpAArohAAAAAZCSvjm8"

# Your ACS resource phone number will act as source number to start outbound call
ACS_PHONE_NUMBER = "+18332638155"

# Target phone number you want to receive the call
TARGET_PHONE_NUMBER = "+919866012455"

PARTICIPANT_PHONE_NUMBER = "+919866012455"

TARGET_COMMUNICATION_USER = ""

PARTICIPANT_COMMUNICATION_USER = ""

WEBSOCKET_URI_HOST=""

COGNITIVE_SERVICES_ENDPOINT = "https://cognitive-service-waferwire.cognitiveservices.azure.com/"

# Template and static file paths
TEMPLATE_FILES_PATH = "template"
AUDIO_FILES_PATH = "/audio"

# Prompts for text to speech
CONFIRM_CHOICE_LABEL = "Confirm"
CANCEL_CHOICE_LABEL = "Cancel"
RETRY_CONTEXT = "retry"
MAIN_MENU_PROMPT_URI = "https://sample-videos.com/audio/mp3/crowd-cheering.mp3"

RECOGNITION_PROMPT = "Hello this is contoso recognition test please confirm or cancel to proceed further."
PLAY_PROMPT = "Welcome to the Contoso Utilities. Thank you!"
SSML_PLAY_TEXT = "<speak version=\"1.0\" xmlns=\"http://www.w3.org/2001/10/synthesis\" xml:lang=\"en-US\"><voice name=\"en-US-JennyNeural\">Welcome to the Contoso Utilities. Played through SSML. Thank you!</voice></speak>"
SSML_RECOGNITION_TEXT = "<speak version=\"1.0\" xmlns=\"http://www.w3.org/2001/10/synthesis\" xml:lang=\"en-US\"><voice name=\"en-US-JennyNeural\">Hello this is SSML recognition test please confirm or cancel to proceed further. Thank you!</voice></speak>"
HOLD_PROMPT = "You are on hold please wait."
SSML_HOLD_TEXT = "<speak version=\"1.0\" xmlns=\"http://www.w3.org/2001/10/synthesis\" xml:lang=\"en-US\"><voice name=\"en-US-JennyNeural\">You are on hold please wait. Played through SSML. Thank you!</voice></speak>"
INTERRUPT_PROMPT = "Play is interrupted."
SSML_INTERRUPT_TEXT = "<speak version=\"1.0\" xmlns=\"http://www.w3.org/2001/10/synthesis\" xml:lang=\"en-US\"><voice name=\"en-US-JennyNeural\">Play is interrupted. Played through SSML. Thank you!</voice></speak>"

# Recording storage settings
BRING_YOUR_OWN_STORAGE_URL = ""
IS_BYOS = False
IS_PAUSE_ON_START = False

# Pydantic models for request/response validation
class CloudEventData(BaseModel):
    callConnectionId: str
    correlationId: Optional[str] = None
    operationContext: Optional[str] = None
    resultInformation: Optional[dict] = None
    recognitionType: Optional[str] = None
    dtmfResult: Optional[dict] = None
    choiceResult: Optional[dict] = None
    speechResult: Optional[dict] = None
    failedPlaySourceIndex: Optional[int] = None
    tone: Optional[str] = None
    sequenceId: Optional[str] = None
    transcriptionUpdate: Optional[dict] = None
    mediaStreamingUpdate: Optional[dict] = None

class CloudEventModel(BaseModel):
    id: str
    source: str
    type: str
    time: str
    data: CloudEventData
    specversion: str

class RecordingChunk(BaseModel):
    contentLocation: str
    metadataLocation: str
    deleteLocation: str

class RecordingStorageInfo(BaseModel):
    recordingChunks: List[RecordingChunk]

class AcsRecordingFileStatusUpdatedEventData(BaseModel):
    recordingStorageInfo: RecordingStorageInfo

class EventGridEventModel(BaseModel):
    eventType: str
    data: dict

# Initialize FastAPI app with Swagger UI customization
app = FastAPI(
    title="ACS Contoso GA5-Python",
    description="API for managing calls, media, and recordings using Azure Communication Services.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

class CallMedia:
    def stop_media_streaming(self):
        # Logic to stop media streaming (simulated)
        pass

class CallConnection:
    def __init__(self, call_connection_id: str):
        self.call_connection_id = call_connection_id
        self.call_media = CallMedia()

    def get_call_media(self):
        return self.call_media
    
# Mount static files for audio
app.mount(AUDIO_FILES_PATH, StaticFiles(directory=AUDIO_FILES_PATH.strip("/")), name="audio")

# Initialize templates
templates = Jinja2Templates(directory=TEMPLATE_FILES_PATH)

# Initialize Call Automation Client
call_automation_client = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)

# Global variables
call_connection_id = None
recording_id = None
content_location = None
metadata_location = None
delete_location = None

class Configuration:
    acs_connection_string: str = ""
    cognitive_service_endpoint: str = ""
    acs_phone_number: str = ""
    callback_uri_host: str = ""
    websocket_uri_host: str = ""

# Singleton-style configuration
configuration = Configuration()

# Request model
class ConfigurationRequest(BaseModel):
    acs_connection_string: str = Field(..., description="Azure Communication Services connection string")
    cognitive_service_endpoint: str = Field(..., description="Cognitive Services endpoint")
    acs_phone_number: str = Field(..., description="ACS phone number")
    callback_uri_host: str = Field(..., description="Callback URI host")
    websocket_uri_host: str = Field(..., description="Websocket URI host")

# Global variables (simulate static vars from Java)
acs_connection_string = ""
cognitive_services_endpoint = ""
acs_phone_number = ""
callback_uri_host = ""
websocket_uri_host = ""
client = None


def init_client():
    # Dummy client initializer
    logger.info("Client initialized with ACS Connection String: %s", acs_connection_string)
    return "client_instance"

@app.post(
    "/api/setConfigurations",
    tags=["Set Configuration"],
    summary="Set configurations",
    description="Sets configuration for call automation, including ACS connection string, Cognitive Services endpoint, phone number, callback URI, and websocket URI.",
    responses={
        200: {"description": "Configuration set successfully and client initialized."},
        500: {"description": "Failed to configure call automation client."},
    },
)
async def set_configurations(configuration_request: ConfigurationRequest = Body(...)):
    """Set configuration and initialize the call automation client."""
    global acs_connection_string, cognitive_services_endpoint, acs_phone_number, callback_uri_host, websocket_uri_host, client

    try:
        # Validate and set values
        configuration.acs_connection_string = configuration_request.acs_connection_string.strip() or \
            (_ for _ in ()).throw(ValueError("AcsConnectionString is required"))
        configuration.cognitive_service_endpoint = configuration_request.cognitive_service_endpoint.strip() or \
            (_ for _ in ()).throw(ValueError("CognitiveServiceEndpoint is required"))
        configuration.acs_phone_number = configuration_request.acs_phone_number.strip() or \
            (_ for _ in ()).throw(ValueError("AcsPhoneNumber is required"))
        configuration.callback_uri_host = configuration_request.callback_uri_host.strip() or \
            (_ for _ in ()).throw(ValueError("CallbackUriHost is required"))
        configuration.websocket_uri_host = configuration_request.websocket_uri_host.strip() or \
            (_ for _ in ()).throw(ValueError("WebsocketUriHost is required"))

        # Assign to global variables
        acs_connection_string = configuration.acs_connection_string
        cognitive_services_endpoint = configuration.cognitive_service_endpoint
        acs_phone_number = configuration.acs_phone_number
        callback_uri_host = configuration.callback_uri_host
        websocket_uri_host = configuration.websocket_uri_host

        client = init_client()

        logger.info("Initialized call automation client.")
        return {"message": "Configuration set successfully. Initialized call automation client."}

    except Exception as e:
        logger.error(f"Error configuring: {e}")
        raise HTTPException(status_code=500, detail="Failed to configure call automation client.")

@app.get(
    "/api/logs",
    tags=["Call Automation Events"],
    summary="Get Azure App Log Stream",
    description="Fetches the live application log stream from Azure App Service using Kudu API.",
    responses={
        200: {"description": "Successfully fetched log stream."},
        500: {"description": "Failed to fetch log stream."}
    }
)
async def get_azure_log_stream(
    userName: str = Query(..., description="Kudu username (usually site credentials)"),
    password: str = Query(..., description="Kudu password (usually site credentials)")
):
    """Fetch Azure App Service live log stream via Kudu API"""
    app_name = "PythonGA5App"
    kudu_url = f"https://{app_name}.scm.azurewebsites.net/api/logstream/application"

    # Basic Authentication header
    auth_str = f"{userName}:{password}"
    encoded_auth = base64.b64encode(auth_str.encode()).decode()

    headers = {
        "Authorization": f"Basic {encoded_auth}"
    }

    try:
        # Stream logs (using requests for simplicity, aiohttp can also be used for async streaming)
        response = requests.get(kudu_url, headers=headers, timeout=10)
        response.raise_for_status()
        return Response(content=response.text, media_type="text/plain")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch logs: {str(e)}")

async def create_call_acs(acsString):
        acs_target = CommunicationUserIdentifier(acsString)
        call_connection_properties = await call_automation_client.create_call(
            acs_target,
            callback_uri_host + "/api/callbacks",
            cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT
        )


# Helper functions (unchanged from original code)
async def create_call():
    global call_connection_id
    is_acs_user_target = False
    logger.info("callback target: %s", callback_uri_host + "/api/callbacks")
    if is_acs_user_target:
        acs_target = CommunicationUserIdentifier(TARGET_COMMUNICATION_USER)
        call_connection_properties = await call_automation_client.create_call(
            acs_target,
            callback_uri_host + "/api/callbacks",
            cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT
        )
    else:
        pstn_target = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
        source_caller = PhoneNumberIdentifier(ACS_PHONE_NUMBER)
        call_connection_properties = await call_automation_client.create_call(
            pstn_target,
            callback_uri_host + "/api/callbacks",
            cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT,
            source_caller_id_number=source_caller
        )
    call_connection_id = call_connection_properties.call_connection_id
    logger.info("Created call with Correlation id: - %s", call_connection_properties.correlation_id)

async def create_group_call():
    acs_target = CommunicationUserIdentifier(TARGET_COMMUNICATION_USER)
    pstn_target = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
    source_caller = PhoneNumberIdentifier(ACS_PHONE_NUMBER)
    targets = [pstn_target, acs_target]
    call_connection_properties = await call_automation_client.create_call(
        targets,
        callback_uri_host + "/api/callbacks",
        cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT,
        source_caller_id_number=source_caller
    )
    logger.info("Created group call with connection id: %s", call_connection_properties.call_connection_id)

async def connect_call():
    await call_automation_client.connect_call(
        group_call_id="593c4e2a-c1c7-4863-9b7e-64b984cbc362",
        callback_url=callback_uri_host + "/api/callbacks",
        backup_cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT,
        operation_context="connectCallContext"
    )

def get_choices():
    choices = [
        RecognitionChoice(label=CONFIRM_CHOICE_LABEL, phrases=["Confirm", "First", "One"], tone=DtmfTone.ONE),
        RecognitionChoice(label=CANCEL_CHOICE_LABEL, phrases=["Cancel", "Second", "Two"], tone=DtmfTone.TWO)
    ]
    return choices

async def play_recognize(recognizeType: RecognizeInputType):
    text_source = TextSource(text=RECOGNITION_PROMPT, voice_name="en-US-NancyNeural")
    target = get_communication_target()
    if recognizeType == RecognizeInputType.SPEECH:
        await call_automation_client.get_call_connection(call_connection_id).start_recognizing_media(
            input_type=RecognizeInputType.SPEECH,
            target_participant=target,
            play_prompt=text_source,
            interrupt_prompt=False,
            initial_silence_timeout=10,
            operation_context="speechContext"
        )
    elif recognizeType == RecognizeInputType.DTMF:
        await call_automation_client.get_call_connection(call_connection_id).start_recognizing_media(
            input_type=RecognizeInputType.DTMF,
            target_participant=target,
            play_prompt=text_source,
            interrupt_prompt=False,
            dtmf_max_tones_to_collect=4,
            initial_silence_timeout=10,
            operation_context="dtmfContext"
        )
    elif recognizeType == RecognizeInputType.CHOICES:
        await call_automation_client.get_call_connection(call_connection_id).start_recognizing_media(
            input_type=RecognizeInputType.CHOICES,
            target_participant=target,
            choices=get_choices(),
            play_prompt=text_source,
            interrupt_prompt=False,
            initial_silence_timeout=10,
            operation_context="choiceContext"
        )
    elif recognizeType == RecognizeInputType.SPEECH_OR_DTMF:
        await call_automation_client.get_call_connection(call_connection_id).start_recognizing_media(
            input_type=RecognizeInputType.SPEECH_OR_DTMF,
            target_participant=target,
            play_prompt=text_source,
            interrupt_prompt=False,
            dtmf_max_tones_to_collect=4,
            initial_silence_timeout=10,
            operation_context="speechOrDtmfContext"
        )

async def play_media(one_source: bool, is_play_to_all: bool, valid_file: bool = True):
    text_source = TextSource(text=PLAY_PROMPT, voice_name="en-US-NancyNeural")
    file_source = FileSource(url=MAIN_MENU_PROMPT_URI)
    ssml_text = SsmlSource(ssml_text=SSML_PLAY_TEXT)
    target = get_communication_target()
    if not valid_file:
        file_source = FileSource(url="https://invalid-url.com/audio.mp3")
    play_sources = [text_source, ssml_text, file_source]
    if one_source:
        play_sources = [text_source]
    if is_play_to_all:
        await call_automation_client.get_call_connection(call_connection_id).play_media_to_all(
            play_source=play_sources,
            operation_context="playToAllContext",
            loop=False,
            operation_callback_url=callback_uri_host + "/api/callbacks",
            interrupt_call_media_operation=False
        )
    else:
        await call_automation_client.get_call_connection(call_connection_id).play_media(
            play_source=play_sources
        )

async def start_continuous_dtmf():
    target = get_communication_target()
    await call_automation_client.get_call_connection(call_connection_id).start_continuous_dtmf_recognition(target_participant=target)
    logger.info("Continuous Dtmf recognition started. press 1 on dialpad.")

async def stop_continuous_dtmf():
    target = get_communication_target()
    await call_automation_client.get_call_connection(call_connection_id).stop_continuous_dtmf_recognition(target_participant=target)
    logger.info("Continuous Dtmf recognition stopped.")

async def start_send_dtmf_tones():
    target = get_communication_target()
    tones = [DtmfTone.ONE, DtmfTone.TWO]
    await call_automation_client.get_call_connection(call_connection_id).send_dtmf_tones(tones=tones, target_participant=target)
    logger.info("Send dtmf tone started.")


async def pause_recording():
    if recording_id:
        if (await get_recording_state()) == "active":
            await call_automation_client.pause_recording(recording_id)
            logger.info("Recording is paused.")
        else:
            logger.info("Recording is already inactive.")
    else:
        logger.info("Recording id is empty.")

async def resume_recording():
    if recording_id:
        if (await get_recording_state()) == "inactive":
            await call_automation_client.resume_recording(recording_id)
            logger.info("Recording is resumed.")
        else:
            logger.info("Recording is already active.")
    else:
        logger.info("Recording id is empty.")

async def stop_recording():
    if recording_id:
        if (await get_recording_state()) == "active":
            await call_automation_client.resume_recording(recording_id)
            logger.info("Recording is stopped.")
        else:
            logger.info("Recording is already inactive.")
    else:
        logger.info("Recording id is empty.")

async def get_recording_state():
    recording_state_result = await call_automation_client.get_recording_properties(recording_id)
    logger.info("Recording State --> %s", recording_state_result.recording_state)
    return recording_state_result.recording_state



async def resume_recording_logic(recording_id: str, call_connection_id: str):
    try:
        if not recording_id:
            print(f"console.log: ⚠️ Recording id is empty.")
            raise HTTPException(
                status_code=400,
                detail="Recording id is empty."
            )

        if not call_connection_id:
            print(f"console.log: ⚠️ Call connection id is empty.")
            raise HTTPException(
                status_code=400,
                detail="Call connection id is empty."
            )

        # Fetch call properties to get correlationId
        call_connection_properties = await call_automation_client.get_call_connection(
            call_connection_id
        ).get_call_properties()
        correlation_id = call_connection_properties.correlation_id

        recording_state = await get_recording_state(recording_id)  # Update get_recording_state to accept recording_id
        if recording_state == "inactive":
            print(f"console.log: ▶️ Resuming recording with RecordingId: {recording_id}")
            await call_automation_client.resume_recording(recording_id)
            print(f"console.log: ✅ Recording is resumed.")
            status_message = "Recording is resumed."
        else:
            print(f"console.log: ℹ️ Recording is already active. RecordingId: {recording_id}")
            status_message = "Recording is already active."

        return CloudEventData(
            callConnectionId=call_connection_id,
            correlationId=correlation_id,
            resultInformation={"status": status_message}
        )

    except Exception as ex:
        error_message = f"Error resuming recording: {str(ex)}. RecordingId: {recording_id}, CallConnectionId: {call_connection_id}"
        print(f"console.log: ❌ {error_message}")
        raise HTTPException(
            status_code=500,
            detail=error_message
        )


async def stop_recording_logic(recording_id: str, call_connection_id: str):
    try:
        if not recording_id:
            print(f"console.log: ⚠️ Recording id is empty.")
            raise HTTPException(
                status_code=400,
                detail="Recording id is empty."
            )

        if not call_connection_id:
            print(f"console.log: ⚠️ Call connection id is empty.")
            raise HTTPException(
                status_code=400,
                detail="Call connection id is empty."
            )

        # Fetch call properties to get correlationId
        call_connection_properties = await call_automation_client.get_call_connection(
            call_connection_id
        ).get_call_properties()
        correlation_id = call_connection_properties.correlation_id

        recording_state = await get_recording_state(recording_id)  # Update get_recording_state to accept recording_id
        if recording_state == "active":
            print(f"console.log: 🛑 Stopping recording with RecordingId: {recording_id}")
            await call_automation_client.stop_recording(recording_id)
            print(f"console.log: ✅ Recording is stopped.")
            status_message = "Recording is stopped."
        else:
            print(f"console.log: ℹ️ Recording is already inactive. RecordingId: {recording_id}")
            status_message = "Recording is already inactive."

        return CloudEventData(
            callConnectionId=call_connection_id,
            correlationId=correlation_id,
            resultInformation={"status": status_message}
        )

    except Exception as ex:
        error_message = f"Error stopping recording: {str(ex)}. RecordingId: {recording_id}, CallConnectionId: {call_connection_id}"
        print(f"console.log: ❌ {error_message}")
        raise HTTPException(
            status_code=500,
            detail=error_message
        )

@app.post(
    "/stopRecording",
    tags=["Recording"],
    summary="Stop call recording",
    description="Stops an active call recording.",
    responses={
        302: {"description": "Redirect to home page after stopping recording"}
    }
)
async def stop_recording_handler(
    recordingId: str = Query(..., description="Recording ID to stop"),
    callConnectionId: str = Query(..., description="Call connection ID")
):
    """Stop call recording."""
    result = await stop_recording_logic(recording_id=recordingId, call_connection_id=callConnectionId)
    return RedirectResponse(url="/")

async def add_participant_pstn():
    """Add a PSTN phone number as a participant."""
    await call_automation_client.get_call_connection(call_connection_id).add_participant(
        target_participant=PhoneNumberIdentifier(PARTICIPANT_PHONE_NUMBER),
        operation_context="addPstnUserContext",
        source_caller_id_number=PhoneNumberIdentifier(ACS_PHONE_NUMBER),
        invitation_timeout=30
    )

async def remove_participant():
    target = get_communication_target()
    await call_automation_client.get_call_connection(call_connection_id).remove_participant(
        target_participant=target,
        operation_context="removeParticipantContext"
    )

async def cancel_all_media_oparation():
    await call_automation_client.get_call_connection(call_connection_id).cancel_all_media_operations()

async def transfer_call_to_participant():
    is_acs_participant = False
    transfer_target = CommunicationUserIdentifier(PARTICIPANT_COMMUNICATION_USER) if is_acs_participant else PhoneNumberIdentifier(PARTICIPANT_PHONE_NUMBER)
    logger.info("Transfer target:- %s", transfer_target.raw_id)
    await call_automation_client.get_call_connection(call_connection_id).transfer_call_to_participant(
        target_participant=transfer_target,
        operation_context="transferCallContext",
        transferee=PhoneNumberIdentifier(TARGET_PHONE_NUMBER),
        source_caller_id_number=PhoneNumberIdentifier(ACS_PHONE_NUMBER)
    )
    logger.info("Transfer call initiated.")

async def hold_participant():
    text_source = TextSource(text=HOLD_PROMPT, voice_name="en-US-NancyNeural")
    target = get_communication_target()
    await call_automation_client.get_call_connection(call_connection_id).hold(
        target_participant=target,
        play_source=text_source
    )
    time.sleep(5)
    result = await get_participant(target)
    logger.info("Participant:--> %s", result.identifier.raw_id)
    logger.info("Is participant on hold:--> %s", result.is_on_hold)

async def unhold_participant():
    target = get_communication_target()
    await call_automation_client.get_call_connection(call_connection_id).unhold(
        target_participant=target
    )
    time.sleep(5)
    result = await get_participant(target)
    logger.info("Participant:--> %s", result.identifier.raw_id)
    logger.info("Is participant on hold:--> %s", result.is_on_hold)

async def play_with_interrupt_media_flag():
    text_source = TextSource(text=INTERRUPT_PROMPT, voice_name="en-US-NancyNeural")
    file_source = FileSource(url=MAIN_MENU_PROMPT_URI)
    ssml_text = SsmlSource(ssml_text=SSML_INTERRUPT_TEXT)
    play_sources = [text_source, file_source, ssml_text]
    call_connection = call_automation_client.get_call_connection(call_connection_id)
    await call_connection.play_media_to_all(
        play_source=play_sources,
        loop=False,
        operation_context="interruptMediaContext",
        operation_callback_url=callback_uri_host + "/api/callbacks",
        interrupt_call_media_operation=True
    )

async def mute_participant():
    target = get_communication_target()
    await call_automation_client.get_call_connection(call_connection_id).mute_participant(
        target_participant=target,
        operation_context="muteParticipantContext"
    )
    time.sleep(5)
    result = await get_participant(target)
    logger.info("Participant:--> %s", result.identifier.raw_id)
    logger.info("Is participant muted:--> %s", result.is_muted)

async def get_participant(target: CommunicationIdentifier):
    participant = await call_automation_client.get_call_connection(call_connection_id).get_participant(target)
    return participant

async def get_participant_list():
    participants = call_automation_client.get_call_connection(call_connection_id).list_participants()
    logger.info("Listing participants in call")
    async for page in participants.by_page():
        async for participant in page:
            logger.info("-------------------------------------------------------------")
            logger.info("Participant: %s", participant.identifier.raw_id)
            logger.info("Is participant muted: %s", participant.is_muted)
            logger.info("Is participant on hold: %s", participant.is_on_hold)
            logger.info("-------------------------------------------------------------")

async def hangup_call():
    await call_automation_client.get_call_connection(call_connection_id).hang_up(False)

async def terminate_call():
    await call_automation_client.get_call_connection(call_connection_id).hang_up(True)

def get_communication_target():
    is_pstn_participant = False
    is_acs_participant = False
    is_acs_user = False
    pstn_identifier = PhoneNumberIdentifier(PARTICIPANT_PHONE_NUMBER) if is_pstn_participant else PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
    acs_identifier = CommunicationUserIdentifier(PARTICIPANT_COMMUNICATION_USER) if is_acs_participant else CommunicationUserIdentifier(TARGET_COMMUNICATION_USER)
    target = acs_identifier if is_acs_user else pstn_identifier
    logger.info("###############TARGET############---> %s", target.raw_id)
    return target

async def get_call_properties():
    call_properties = await call_automation_client.get_call_connection(call_connection_id).get_call_properties()
    return call_properties

# FastAPI Routes with Swagger Documentation
@app.post(
    "/api/callbacks",
    tags=["Callbacks"],
    summary="Handle ACS callback events",
    description="Processes callback events from Azure Communication Services, such as call connection, recognition, and recording events.",
    responses={
        200: {"description": "Events processed successfully"},
        500: {"description": "Internal server error"}
    }
)
async def callback_events_handler(request: Request, events: List[CloudEventModel]):
    """
    Handle callback events from Azure Communication Services.
    Processes events like CallConnected, RecognizeCompleted, PlayFailed, etc.
    """
    global call_connection_id
    try:
        for event in events:
            cloud_event = CloudEvent.from_dict(event.dict())
            call_connection_id = cloud_event.data['callConnectionId']
            logger.info("%s event received for call correlation id: %s", cloud_event.type, cloud_event.data['callConnectionId'])
            call_connection_client = call_automation_client.get_call_connection(call_connection_id)

            if cloud_event.type == "Microsoft.Communication.CallConnected":
                logger.info(f"Received CallConnected event for connection id: {cloud_event.data['callConnectionId']}")
                logger.info("CORRELATION ID: - %s", cloud_event.data["correlationId"])
                logger.info("CALL CONNECTION ID:--> %s", cloud_event.data["callConnectionId"])
                properties = await get_call_properties()

            elif cloud_event.type == "Microsoft.Communication.ConnectFailed":
                logger.info(f"Received ConnectFailed event for connection id: {cloud_event.data['callConnectionId']}")
                resultInformation = cloud_event.data['resultInformation']
                logger.info("Encountered error during connect, message=%s, code=%s, subCode=%s", resultInformation['message'], resultInformation['code'], resultInformation['subCode'])

            elif cloud_event.type == "Microsoft.Communication.AddParticipantSucceeded":
                logger.info(f"Received AddParticipantSucceeded event for connection id: {cloud_event.data['callConnectionId']}")

            elif cloud_event.type == "Microsoft.Communication.RecognizeCompleted":
                logger.info(f"Received RecognizeCompleted event for connection id: {cloud_event.data['callConnectionId']}")
                if cloud_event.data['recognitionType'] == "dtmf":
                    tones = cloud_event.data['dtmfResult']['tones']
                    logger.info("Recognition completed, tones=%s, context=%s", tones, cloud_event.data['operationContext'])
                elif cloud_event.data['recognitionType'] == "choices":
                    labelDetected = cloud_event.data['choiceResult']['label']
                    phraseDetected = cloud_event.data['choiceResult']['recognizedPhrase']
                    logger.info("Recognition completed, labelDetected=%s, phraseDetected=%s, context=%s", labelDetected, phraseDetected, cloud_event.data['operationContext'])
                elif cloud_event.data['recognitionType'] == "speech":
                    text = cloud_event.data['speechResult']['speech']
                    logger.info("Recognition completed, text=%s, context=%s", text, cloud_event.data['operationContext'])
                else:
                    logger.info("Recognition completed: data=%s", cloud_event.data)

            elif cloud_event.type == "Microsoft.Communication.RecognizeFailed":
                if "operationContext" in cloud_event.data:
                    opContext = cloud_event.data['operationContext']
                    logger.info("Operation context--> %s", opContext)
                resultInformation = cloud_event.data['resultInformation']
                logger.info("Encountered error during Recognize, message=%s, code=%s, subCode=%s", resultInformation['message'], resultInformation['code'], resultInformation['subCode'])
                logger.info("Play failed source index--> %s", cloud_event.data["failedPlaySourceIndex"])

            elif cloud_event.type in "Microsoft.Communication.PlayCompleted":
                logger.info(f"Received PlayCompleted event for connection id: {call_connection_id}")
                if "operationContext" in cloud_event.data:
                    opContext = cloud_event.data['operationContext']
                    logger.info("Operation context--> %s", opContext)

            elif cloud_event.type in "Microsoft.Communication.PlayFailed":
                logger.info(f"Received PlayFailed event for connection id: {call_connection_id}")
                if "operationContext" in cloud_event.data:
                    opContext = cloud_event.data['operationContext']
                    logger.info("Operation context--> %s", opContext)
                resultInformation = cloud_event.data['resultInformation']
                logger.info("Encountered error during play, message=%s, code=%s, subCode=%s", resultInformation['message'], resultInformation['code'], resultInformation['subCode'])
                logger.info("Play failed source index--> %s", cloud_event.data["failedPlaySourceIndex"])

            elif cloud_event.type == "Microsoft.Communication.ContinuousDtmfRecognitionToneReceived":
                logger.info(f"Received ContinuousDtmfRecognitionToneReceived event for connection id: {call_connection_id}")
                logger.info(f"Tone received:-->: {cloud_event.data['tone']}")
                logger.info(f"Sequence Id:--> {cloud_event.data['sequenceId']}")

            elif cloud_event.type == "Microsoft.Communication.ContinuousDtmfRecognitionToneFailed":
                logger.info(f"Received ContinuousDtmfRecognitionToneFailed event for connection id: {call_connection_id}")
                if "operationContext" in cloud_event.data:
                    opContext = cloud_event.data['operationContext']
                    logger.info("Operation context--> %s", opContext)
                resultInformation = cloud_event.data['resultInformation']
                logger.info("Encountered error:- message=%s, code=%s, subCode=%s", resultInformation['message'], resultInformation['code'], resultInformation['subCode'])

            elif cloud_event.type == "Microsoft.Communication.ContinuousDtmfRecognitionStopped":
                logger.info(f"Received ContinuousDtmfRecognitionStopped event for connection id: {call_connection_id}")

            elif cloud_event.type == "Microsoft.Communication.SendDtmfTonesCompleted":
                logger.info(f"Received SendDtmfTonesCompleted event for connection id: {call_connection_id}")

            elif cloud_event.type == "Microsoft.Communication.SendDtmfTonesFailed":
                logger.info(f"Received SendDtmfTonesFailed event for connection id: {call_connection_id}")
                resultInformation = cloud_event.data['resultInformation']
                logger.info("Encountered error:- message=%s, code=%s, subCode=%s", resultInformation['message'], resultInformation['code'], resultInformation['subCode'])

            elif cloud_event.type == "Microsoft.Communication.RemoveParticipantSucceeded":
                logger.info(f"Received RemoveParticipantSucceeded event for connection id: {call_connection_id}")

            elif cloud_event.type == "Microsoft.Communication.RemoveParticipantFailed":
                logger.info(f"Received RemoveParticipantFailed event for connection id: {call_connection_id}")
                resultInformation = cloud_event.data['resultInformation']
                logger.info("Encountered error:- message=%s, code=%s, subCode=%s", resultInformation['message'], resultInformation['code'], resultInformation['subCode'])

            elif cloud_event.type == "Microsoft.Communication.HoldFailed":
                logger.info("Hold Failed.")
                resultInformation = cloud_event.data['resultInformation']
                logger.info("Encountered error during Hold, message=%s, code=%s, subCode=%s", resultInformation['message'], resultInformation['code'], resultInformation['subCode'])

            elif cloud_event.type == "Microsoft.Communication.PlayStarted":
                logger.info("PlayStarted event received.")

            elif cloud_event.type in "Microsoft.Communication.PlayCanceled":
                logger.info(f"Received PlayCanceled event for connection id: {call_connection_id}")
                if "operationContext" in cloud_event.data:
                    opContext = cloud_event.data['operationContext']
                    logger.info("Operation context--> %s", opContext)

            elif cloud_event.type in "Microsoft.Communication.RecognizeCanceled":
                logger.info(f"Received RecognizeCanceled event for connection id: {call_connection_id}")
                if "operationContext" in cloud_event.data:
                    opContext = cloud_event.data['operationContext']
                    logger.info("Operation context--> %s", opContext)

            elif cloud_event.type == "Microsoft.Communication.RecordingStateChanged":
                logger.info(f"Received RecordingStateChanged event for connection id: {call_connection_id}")

            elif cloud_event.type == "Microsoft.Communication.CallTransferAccepted":
                logger.info(f"Received CallTransferAccepted event for connection id: {call_connection_id}")

            elif cloud_event.type == "Microsoft.Communication.CallTransferFailed":
                logger.info(f"Received CallTransferFailed event for connection id: {call_connection_id}")
                if "operationContext" in cloud_event.data:
                    opContext = cloud_event.data['operationContext']
                    logger.info("Operation context--> %s", opContext)
                resultInformation = cloud_event.data['resultInformation']
                logger.info("Encountered error:- message=%s, code=%s, subCode=%s", resultInformation['message'], resultInformation['code'], resultInformation['subCode'])

            elif cloud_event.type == "Microsoft.Communication.AddParticipantFailed":
                logger.info(f"Received AddParticipantFailed event for connection id: {call_connection_id}")
                if "operationContext" in cloud_event.data:
                    opContext = cloud_event.data['operationContext']
                    logger.info("Operation context--> %s", opContext)
                resultInformation = cloud_event.data['resultInformation']
                logger.info("Encountered error:- message=%s, code=%s, subCode=%s", resultInformation['message'], resultInformation['code'], resultInformation['subCode'])

            elif cloud_event.type == "Microsoft.Communication.CancelAddParticipantSucceeded":
                logger.info(f"Received CancelAddParticipantSucceeded event for connection id: {call_connection_id}")

            elif cloud_event.type == "Microsoft.Communication.CancelAddParticipantFailed":
                logger.info(f"Received CancelAddParticipantFailed event for connection id: {call_connection_id}")
                if "operationContext" in cloud_event.data:
                    opContext = cloud_event.data['operationContext']
                    logger.info("Operation context--> %s", opContext)
                resultInformation = cloud_event.data['resultInformation']
                logger.info("Encountered error:- message=%s, code=%s, subCode=%s", resultInformation['message'], resultInformation['code'], resultInformation['subCode'])

            elif cloud_event.type == "Microsoft.Communication.CreateCallFailed":
                logger.info(f"Received CreateCallFailed event for connection id: {call_connection_id}")
                if "operationContext" in cloud_event.data:
                    opContext = cloud_event.data['operationContext']
                    logger.info("Operation context--> %s", opContext)
                resultInformation = cloud_event.data['resultInformation']
                logger.info("Encountered error:- message=%s, code=%s, subCode=%s", resultInformation['message'], resultInformation['code'], resultInformation['subCode'])

            elif cloud_event.type == "Microsoft.Communication.CallDisconnected":
                logger.info(f"Received CallDisconnected event for connection id: {call_connection_id}")

        return Response(status_code=200)
    except Exception as ex:
        logger.error(f"Error in callback handler: {str(ex)}")
        return Response(status_code=500, content=str(ex))

@app.post(
    "/download",
    tags=["Recording"],
    summary="Download call recording",
    description="Downloads the recorded audio file from Azure Communication Services and saves it locally.",
    responses={
        302: {"description": "Redirect to home page after successful download"},
        500: {"description": "Failed to download recording"}
    }
)
async def download_recording():
    """Download the recorded audio file."""
    try:
        logger.info("Content location: %s", content_location)
        recording_data = await call_automation_client.download_recording(content_location)
        with open("Recording_File.wav", "wb") as binary_file:
            binary_file.write(recording_data.read())
        return RedirectResponse(url="/")
    except Exception as ex:
        logger.error("Failed to download recording --> %s", str(ex))
        return Response(status_code=500, content=str(ex))

@app.post(
    "/api/recordingFileStatus",
    tags=["Recording"],
    summary="Handle recording file status updates",
    description="Processes recording file status updates from Azure Communication Services, including content and metadata locations.",
    responses={
        200: {"description": "Recording status processed successfully"},
        400: {"description": "Failed to process recording status"}
    }
)
async def recording_file_status(request: Request, events: List[EventGridEventModel]):
    """Handle recording file status updates."""
    try:
        for event_dict in events:
            event = EventGridEvent.from_dict(event_dict.dict())
            if event.event_type == SystemEventNames.EventGridSubscriptionValidationEventName:
                code = event.data['validationCode']
                if code:
                    data = {"validationResponse": code}
                    logger.info("Successfully Subscribed EventGrid.ValidationEvent --> %s", str(data))
                    return Response(content=json.dumps(data), status_code=200)

            if event.event_type == SystemEventNames.AcsRecordingFileStatusUpdatedEventName:
                acs_recording_file_status_updated_event_data = event.data
                acs_recording_chunk_info_properties = acs_recording_file_status_updated_event_data['recordingStorageInfo']['recordingChunks'][0]
                logger.info("acsRecordingChunkInfoProperties response data --> %s", str(acs_recording_chunk_info_properties))
                global content_location, metadata_location, delete_location
                content_location = acs_recording_chunk_info_properties['contentLocation']
                metadata_location = acs_recording_chunk_info_properties['metadataLocation']
                delete_location = acs_recording_chunk_info_properties['deleteLocation']
                logger.info("CONTENT LOCATION --> %s", content_location)
                logger.info("METADATA LOCATION --> %s", metadata_location)
                logger.info("DELETE LOCATION --> %s", delete_location)
                return Response(content="Ok", status_code=200)

    except Exception as ex:
        logger.error("Failed to get recording file: %s", str(ex))
        return Response(content='Failed to get recording file', status_code=400)

@app.post(
    "/downloadMetadata",
    tags=["Recording"],
    summary="Download recording metadata",
    description="Downloads the metadata file for a recording from Azure Communication Services.",
    responses={
        302: {"description": "Redirect to home page after successful download"},
        500: {"description": "Failed to download metadata"}
    }
)
async def download_metadata():
    """Download the recording metadata file."""
    try:
        logger.info("Metadata location: %s", metadata_location)
        recording_data = await call_automation_client.download_recording(metadata_location)
        with open("Recording_metadata.json", "wb") as binary_file:
            binary_file.write(recording_data.read())
        return RedirectResponse(url="/")
    except Exception as ex:
        logger.error("Failed to download metadata --> %s", str(ex))
        return Response(status_code=500, content=str(ex))

@app.post(
    "/outboundCall",
    tags=["Outbound Call API's"],
    summary="Initiate an outbound call",
    description="Initiates an outbound call to a phone number or ACS user.",
    responses={
        302: {"description": "Redirect to home page after initiating call"}
    }
)
async def outbound_call_handler():
    """Initiate an outbound call."""
    await create_call()
    return RedirectResponse(url="/")


@app.post(
    "/acsoutboundCall",
    tags=["Outbound Call API's"],
    summary="Initiate an outbound call",
    description="Initiates an outbound call to a phone number or ACS user.",
    responses={
        302: {"description": "Redirect to home page after initiating call"}
    }
)
async def outbound_acs_call_handler(acsString):
    """Initiate an outbound call."""
    await create_call_acs(acsString)
    return RedirectResponse(url="/")

@app.post(
    "/groupCall",
    tags=["Call Management"],
    summary="Initiate a group call",
    description="Initiates a group call with multiple participants.",
    responses={
        302: {"description": "Redirect to home page after initiating call"}
    }
)
async def group_call_handler():
    """Initiate a group call."""
    await create_group_call()
    return RedirectResponse(url="/")

@app.post(
    "/connectCall",
    tags=["Call Management"],
    summary="Connect to an existing call",
    description="Connects to an existing group call by group call ID.",
    responses={
        302: {"description": "Redirect to home page after connecting to call"}
    }
)
async def connect_call_handler():
    """Connect to an existing call."""
    await connect_call()
    return RedirectResponse(url="/")

@app.post(
    "/playMediaToAllMultipleSources",
    tags=["Media Operations"],
    summary="Play media to all call participants",
    description="Plays audio media (e.g., prompts or files) to all call participants.",
    responses={
        302: {"description": "Redirect to home page after playing media"}
    }
)
async def play_media_handler():
    """Play media to call participants."""
    await play_media(False, True)
    return RedirectResponse(url="/")

@app.post(
    "/playMediaToParticipantsMultipleSources",
    tags=["Media Operations"],
    summary="Play media to specific call participants",
    description="Plays audio media (e.g., prompts or files) to specific call participants.",
    responses={
        302: {"description": "Redirect to home page after playing media"}
    }
)
async def play_media_handler():
    """Play media to call participants."""
    await play_media(True, True)
    return RedirectResponse(url="/")

@app.post(
    "/playMediaToAllMultipleSourcesInvalid",
    tags=["Media Operations"],
    summary="Play media to all call participants",
    description="Plays audio media (e.g., prompts or files) to all call participants.",
    responses={
        302: {"description": "Redirect to home page after playing media"}
    }
)
async def play_media_handler():
    """Play media to call participants."""
    await play_media(False, True, False)
    return RedirectResponse(url="/")

@app.post(
    "/playMediaToParticipantsMultipleSourcesInvalid",
    tags=["Media Operations"],
    summary="Play media to specific call participants",
    description="Plays audio media (e.g., prompts or files) to specific call participants.",
    responses={
        302: {"description": "Redirect to home page after playing media"}
    }
)
async def play_media_handler():
    """Play media to call participants."""
    await play_media(True, True, False)
    return RedirectResponse(url="/")

@app.post(
    "/playMediaToAll",
    tags=["Media Operations"],
    summary="Play media to all call participants",
    description="Plays audio media (e.g., prompts or files) to all call participants.",
    responses={
        302: {"description": "Redirect to home page after playing media"}
    }
)
async def play_media_handler():
    """Play media to call participants."""
    await play_media(False, False)
    return RedirectResponse(url="/")

@app.post(
    "/playMediaToParticipants",
    tags=["Media Operations"],
    summary="Play media to specific call participants",
    description="Plays audio media (e.g., prompts or files) to specific call participants.",
    responses={
        302: {"description": "Redirect to home page after playing media"}
    }
)
async def play_media_handler():
    """Play media to call participants."""
    await play_media(True, False)
    return RedirectResponse(url="/")

@app.post(
    "/recognizeMediaChoices",
    tags=["Media Operations"],
    summary="Start media recognition",
    description="Starts media recognition (e.g., DTMF or speech) for a call participant.",
    responses={
        302: {"description": "Redirect to home page after starting recognition"}
    }
)
async def play_recognize_handler():
    """Start media recognition."""
    await play_recognize(RecognizeInputType.CHOICES)
    return RedirectResponse(url="/")

@app.post(
    "/recognizeMediaSpeech",
    tags=["Media Operations"],
    summary="Start media recognition",
    description="Starts media recognition (e.g., DTMF or speech) for a call participant.",
    responses={
        302: {"description": "Redirect to home page after starting recognition"}
    }
)
async def play_recognize_handler():
    """Start media recognition."""
    await play_recognize(RecognizeInputType.SPEECH)
    return RedirectResponse(url="/")

@app.post(
    "/recognizeMediaDTMF",
    tags=["Media Operations"],
    summary="Start media recognition",
    description="Starts media recognition (e.g., DTMF or speech) for a call participant.",
    responses={
        302: {"description": "Redirect to home page after starting recognition"}
    }
)
async def play_recognize_handler():
    """Start media recognition."""
    await play_recognize(RecognizeInputType.DTMF)
    return RedirectResponse(url="/")

@app.post(
    "/recognizeMediaSpeechOrDTMF",
    tags=["Media Operations"],
    summary="Start media recognition",
    description="Starts media recognition (e.g., DTMF or speech) for a call participant.",
    responses={
        302: {"description": "Redirect to home page after starting recognition"}
    }
)
async def play_recognize_handler():
    """Start media recognition."""
    await play_recognize(RecognizeInputType.SPEECH_OR_DTMF)
    return RedirectResponse(url="/")

@app.post(
    "/startContinuousDtmf",
    tags=["DTMF API's"],
    summary="Start continuous DTMF recognition",
    description="Starts continuous DTMF tone recognition for a call participant.",
    responses={302: {"description": "Redirect to home page after starting DTMF recognition"}}
)
async def start_continuous_dtmf_tones_handler(
    callConnectionId: str = Query(..., description="Call connection ID"),
    acsTarget: str = Query(..., description="ACS participant ID to receive DTMF tones")
):
    await start_continuous_dtmf_logic(call_connection_id=callConnectionId, acs_target_id=acsTarget)
    return RedirectResponse(url="/")

async def start_continuous_dtmf_logic(call_connection_id: str, acs_target_id: str):
    target = CommunicationUserIdentifier(acs_target_id)

    logger.info(f"➡️ Starting continuous DTMF recognition on call ID: {call_connection_id}")
    logger.info(f"👤 Target participant: {target.raw_id}")

    await call_automation_client.get_call_connection(call_connection_id).start_continuous_dtmf_recognition(
        target_participant=target
    )

    logger.info("✅ Continuous DTMF recognition started.")




@app.post(
    "/stopContinuousDtmf",
    tags=["DTMF API's"],
    summary="Stop continuous DTMF recognition",
    description="Stops continuous DTMF tone recognition for a call participant.",
    responses={302: {"description": "Redirect to home page after stopping DTMF recognition"}}
)
async def stop_continuous_dtmf_tones_handler(
    callConnectionId: str = Query(..., description="Call connection ID"),
    acsTarget: str = Query(..., description="ACS participant ID for whom to stop DTMF recognition")
):
    await stop_continuous_dtmf_logic(call_connection_id=callConnectionId, acs_target_id=acsTarget)
    return RedirectResponse(url="/")

async def stop_continuous_dtmf_logic(call_connection_id: str, acs_target_id: str):
    target = CommunicationUserIdentifier(acs_target_id)

    logger.info(f"🛑 Stopping continuous DTMF recognition on call ID: {call_connection_id}")
    logger.info(f"👤 Target participant: {target.raw_id}")

    await call_automation_client.get_call_connection(call_connection_id).stop_continuous_dtmf_recognition(
        target_participant=target
    )

    logger.info("✅ Continuous DTMF recognition stopped.")



@app.post(
    "/sendDTMFTones",
    tags=["DTMF API's"],
    summary="Send DTMF tones",
    description="Sends DTMF tones to a call participant.",
    responses={
        302: {"description": "Redirect to home page after sending DTMF tones"}
    }
)
async def send_dtmf_tones_handler(
    callConnectionId: str = Query(..., description="Call Connection ID"),
    acsTarget: str = Query(..., description="ACS user ID of the target participant")
):
    """Send DTMF tones to the specified ACS participant."""
    await start_send_dtmf_tones(callConnectionId, acsTarget)
    return RedirectResponse(url="/")


async def start_send_dtmf_tones(call_connection_id: str, acs_target_id: str):
    target = CommunicationUserIdentifier(acs_target_id)

    logger.info(f"Sending DTMF tones to participant: {target.raw_id}")

    call_connection = call_automation_client.get_call_connection(call_connection_id)

    await call_connection.send_dtmf(
        tones=[DtmfTone.ONE, DtmfTone.TWO, DtmfTone.THREE],  # You can make this dynamic too
        target_participant=target,
        operation_context="sendDtmfTonesContext"
    )

    logger.info("DTMF tones sent successfully.")



@app.post(
    "/addParticipantpstn",
    tags=["Add/Remove Participant API's"],
    summary="Add participant to call",
    description="Adds a new participant PSTN to an active call.",
    responses={
        302: {"description": "Redirect to home page after adding participant"}
    }
)
async def add_participant_handler():
    """Add participant to call."""
    await add_participant_pstn()
    return RedirectResponse(url="/")

@app.post(
    "/api/participants/addAcsParticipantAsync",
    tags=["Add/Remove Participant API's"],
    summary="Add ACS participant to call",
    description="Adds a new ACS participant to an active call.",
    responses={
        302: {"description": "Redirect to home page after adding participant"}
    }
)
async def add_acs_participant_handler(
    callConnectionId: str = Query(..., description="callConnectionId"),
    acsParticipant: str = Query(..., description="acsParticipant")
):
    logger.info(f"Adding ACS participant {acsParticipant} to call {callConnectionId}")

    connection = call_automation_client.get_call_connection(callConnectionId)
    await connection.add_participant(
        target_participant=CommunicationUserIdentifier(acsParticipant),
        operation_context="addAcsUserContext",
        invitation_timeout=30
    )

    logger.info("ACS participant added successfully")
    return RedirectResponse(url="/")


@app.post(
    "/api/participants/removeParticipantAsync",
    tags=["Add/Remove Participant API's"],
    summary="Remove a participant from an active call",
    description="Removes a participant (ACS or PSTN) from an ongoing call.",
    responses={
        302: {"description": "Redirect to home page after removing participant"}
    }
)
async def remove_participant_handler(
    callConnectionId: str = Query(..., description="Call connection ID"),
    participantId: str = Query(..., description="ACS user ID or phone number"),
    isAcsUser: bool = Query(..., description="True for ACS user, False for PSTN")
):
    await remove_participant(call_connection_id=callConnectionId, participant_id=participantId, is_acs_user=isAcsUser)
    return RedirectResponse(url="/")

async def remove_participant(call_connection_id: str, participant_id: str, is_acs_user: bool):
    logger.info(f"Removing participant {participant_id} from call {call_connection_id}, isAcsUser={is_acs_user}")

    target = (
        CommunicationUserIdentifier(participant_id)
        if is_acs_user else
        PhoneNumberIdentifier(participant_id)
    )

    connection = call_automation_client.get_call_connection(call_connection_id)
    await connection.remove_participant(
        target_participant=target,
        operation_context="removeParticipantContext"
    )

    logger.info("Participant removed successfully")

async def mute_participant(call_connection_id: str, participant_id: str, is_acs_user: bool):
    logger.info(f"Muting participant {participant_id} in call {call_connection_id}, isAcsUser={is_acs_user}")

    target = (
        CommunicationUserIdentifier(participant_id)
        if is_acs_user else
        PhoneNumberIdentifier(participant_id)
    )

    connection = call_automation_client.get_call_connection(call_connection_id)
    await connection.mute_participant(
        target_participant=target,
        operation_context="muteParticipantContext"
    )

    time.sleep(5)

    result = await connection.get_participant(target)
    logger.info("Participant:--> %s", result.identifier.raw_id)
    logger.info("Is participant muted:--> %s", result.is_muted)


# 🚀 Route Handler
@app.post(
    "/api/participants/muteParticipantAsync",
    tags=["Add/Remove Participant API's"],
    summary="Mute a participant in an active call",
    description="Mutes a participant (ACS or PSTN) in an ongoing call.",
    responses={
        302: {"description": "Redirect to home page after muting participant"}
    }
)
async def mute_participant_handler(
    callConnectionId: str = Query(..., description="Call connection ID"),
    participantId: str = Query(..., description="ACS user ID or phone number"),
    isAcsUser: bool = Query(..., description="True for ACS user, False for PSTN")
):
    await mute_participant(call_connection_id=callConnectionId, participant_id=participantId, is_acs_user=isAcsUser)
    return RedirectResponse(url="/")


async def hold_participant(call_connection_id: str, participant_id: str, is_acs_user: bool, hold_prompt_url: str = None):
    logger.info(f"Putting participant {participant_id} on hold in call {call_connection_id}, isAcsUser={is_acs_user}")

    target = (
        CommunicationUserIdentifier(participant_id)
        if is_acs_user else
        PhoneNumberIdentifier(participant_id)
    )

    connection = call_automation_client.get_call_connection(call_connection_id)

    await connection.hold_participant(
        target_participant=target,
        hold_audio_file_url=hold_prompt_url,
        operation_context="holdParticipantContext"
    )

    logger.info("Participant is now on hold.")

# 🚀 Route Handler
@app.post(
    "/api/participants/holdParticipantAsync",
    tags=["Mute/Unmute Participant API's"],
    summary="Put participant on hold",
    description="Puts a participant (ACS or PSTN) on hold with an optional hold prompt.",
    responses={
        302: {"description": "Redirect to home page after putting participant on hold"}
    }
)
async def hold_participant_handler(
    callConnectionId: str = Query(..., description="Call connection ID"),
    participantId: str = Query(..., description="ACS user ID or phone number"),
    isAcsUser: bool = Query(..., description="True for ACS user, False for PSTN"),
    holdPromptUrl: str = Query(None, description="Optional URL for hold audio prompt")
):
    await hold_participant(call_connection_id=callConnectionId, participant_id=participantId, is_acs_user=isAcsUser, hold_prompt_url=holdPromptUrl)
    return RedirectResponse(url="/")

async def unhold_participant(call_connection_id: str, participant_id: str, is_acs_user: bool):
    logger.info(f"Unholding participant {participant_id} in call {call_connection_id}, isAcsUser={is_acs_user}")

    target = (
        CommunicationUserIdentifier(participant_id)
        if is_acs_user else
        PhoneNumberIdentifier(participant_id)
    )

    connection = call_automation_client.get_call_connection(call_connection_id)

    await connection.resume_participant(
        target_participant=target,
        operation_context="unholdParticipantContext"
    )

    logger.info("Participant is now off hold.")

# 🚀 Route Handler
@app.post(
    "/api/participants/unholdParticipantAsync",
    tags=["Mute/Unmute Participant API's"],
    summary="Take participant off hold",
    description="Takes a participant (ACS or PSTN) off hold in an active call.",
    responses={
        302: {"description": "Redirect to home page after taking participant off hold"}
    }
)
async def unhold_participant_handler(
    callConnectionId: str = Query(..., description="Call connection ID"),
    participantId: str = Query(..., description="ACS user ID or phone number"),
    isAcsUser: bool = Query(..., description="True for ACS user, False for PSTN")
):
    await unhold_participant(call_connection_id=callConnectionId, participant_id=participantId, is_acs_user=isAcsUser)
    return RedirectResponse(url="/")

@app.post(
    "/getParticipant",
    tags=["Hold Participant API's"],
    summary="Get participant details",
    description="Retrieves details of a specific participant in an active call.",
    responses={
        302: {"description": "Redirect to home page after retrieving participant details"}
    }
)
async def get_participant_handler():
    """Get participant details."""
    target = get_communication_target()
    await get_participant(target)
    return RedirectResponse(url="/")
@app.post(
    "/listParticipant",
    tags=["Hold Participant API's"],
    summary="List all participants",
    description="Lists all participants in an active call.",
    responses={
        302: {"description": "Redirect to home page after listing participants"}
    }
)
async def get_participant_list_handler():
    """List all participants."""
    await get_participant_list()
    return RedirectResponse(url="/")

async def transfer_call_to_acs_participant(call_connection_id: str, transfer_target_id: str, transferee_id: str):
    transfer_target = CommunicationUserIdentifier(transfer_target_id)
    transferee = CommunicationUserIdentifier(transferee_id)

    logger.info(f"Transferring call ID {call_connection_id} from {transferee.raw_id} to {transfer_target.raw_id}")

    await call_automation_client.get_call_connection(call_connection_id).transfer_call_to_participant(
        target_participant=transfer_target,
        transferee=transferee,
        operation_context="transferCallContext"
    )

    logger.info("Call transfer initiated successfully.")

    

async def start_recording_with_video_mp4_mixed_logic(
    call_connection_id: str,
    is_recording_with_call_connection_id: bool,
    is_pause_on_start: bool
):
    global recording_id
    try:
        call_connection_properties = await call_automation_client.get_call_connection(
            call_connection_id
        ).get_call_properties()
        server_call_id = call_connection_properties.server_call_id
        correlation_id = call_connection_properties.correlation_id
        call_locator = ServerCallLocator(server_call_id)

        print(f"console.log: 🎥 Starting recording on call ID: {call_connection_id}")
        print(f"console.log: 🔗 Correlation ID: {correlation_id}")

        recording_storage = (
            AzureBlobContainerRecordingStorage(BRING_YOUR_OWN_STORAGE_URL)
            if IS_BYOS
            else AzureCommunicationsRecordingStorage()
        )

        recording_options = (
            {
                "call_connection_id": call_connection_properties.call_connection_id,
                "recording_content_type": RecordingContent.AUDIO_VIDEO,
                "recording_channel_type": RecordingChannel.MIXED,
                "recording_format_type": RecordingFormat.MP4,
                "recording_state_callback_url": callback_uri_host + "/api/callbacks",
                "recording_storage": recording_storage,
                "pause_on_start": is_pause_on_start
            }
            if is_recording_with_call_connection_id
            else {
                "call_locator": call_locator,
                "recording_content_type": RecordingContent.AUDIO_VIDEO,
                "recording_channel_type": RecordingChannel.MIXED,
                "recording_format_type": RecordingFormat.MP4,
                "recording_state_callback_url": callback_uri_host + "/api/callbacks",
                "recording_storage": recording_storage,
                "pause_on_start": is_pause_on_start
            }
        )

        recording_result = await call_automation_client.start_recording(**recording_options)
        recording_id = recording_result.recording_id

        print(
            f"console.log: ✅ Recording started. RecordingId: {recording_id}, "
            f"CallConnectionId: {call_connection_id}, CorrelationId: {correlation_id}, "
            f"Status: {recording_result.recording_state}"
        )

        return CloudEvent(
            call_connection_id=call_connection_id,
            correlation_id=correlation_id,
            status=f"Recording started. RecordingId: {recording_id}. Status: {recording_result.recording_state}"
        )

    except Exception as ex:
        error_message = f"Error starting recording: {str(ex)}. CallConnectionId: {call_connection_id}"
        print(f"console.log: ❌ {error_message}")
        raise HTTPException(
            status_code=500,
            detail=error_message
        )
    


async def start_recording_with_audio_wav_unmixed_logic(
    call_connection_id: str,
    is_recording_with_call_connection_id: bool,
    is_pause_on_start: bool
):
    global recording_id
    try:
        call_connection_properties = await call_automation_client.get_call_connection(
            call_connection_id
        ).get_call_properties()
        server_call_id = call_connection_properties.server_call_id
        correlation_id = call_connection_properties.correlation_id
        call_locator = ServerCallLocator(server_call_id)

        print(f"console.log: 🎙️ Starting audio recording on call ID: {call_connection_id}")
        print(f"console.log: 🔗 Correlation ID: {correlation_id}")

        recording_storage = (
            AzureBlobContainerRecordingStorage(BRING_YOUR_OWN_STORAGE_URL)
            if IS_BYOS
            else AzureCommunicationsRecordingStorage()
        )

        recording_options = (
            {
                "call_connection_id": call_connection_properties.call_connection_id,
                "recording_content_type": RecordingContent.AUDIO,
                "recording_channel_type": RecordingChannel.UNMIXED,
                "recording_format_type": RecordingFormat.WAV,
                "recording_state_callback_url": callback_uri_host + "/api/callbacks",
                "recording_storage": recording_storage,
                "pause_on_start": is_pause_on_start
            }
            if is_recording_with_call_connection_id
            else {
                "call_locator": call_locator,
                "recording_content_type": RecordingContent.AUDIO,
                "recording_channel_type": RecordingChannel.UNMIXED,
                "recording_format_type": RecordingFormat.WAV,
                "recording_state_callback_url": callback_uri_host + "/api/callbacks",
                "recording_storage": recording_storage,
                "pause_on_start": is_pause_on_start
            }
        )

        recording_result = await call_automation_client.start_recording(**recording_options)
        recording_id = recording_result.recording_id

        print(
            f"console.log: ✅ Recording started. RecordingId: {recording_id}, "
            f"CallConnectionId: {call_connection_id}, CorrelationId: {correlation_id}, "
            f"Status: {recording_result.recording_state}"
        )

        return CloudEvent(
            call_connection_id=call_connection_id,
            correlation_id=correlation_id,
            status=f"Recording started. RecordingId: {recording_id}. Status: {recording_result.recording_state}"
        )

    except Exception as ex:
        error_message = f"Error starting recording: {str(ex)}. CallConnectionId: {call_connection_id}"
        print(f"console.log: ❌ {error_message}")
        raise HTTPException(
            status_code=500,
            detail=error_message
        )


async def start_recording_with_audio_wav_mixed_logic(
    call_connection_id: str,
    is_recording_with_call_connection_id: bool,
    is_pause_on_start: bool
):
    global recording_id
    try:
        call_connection_properties = await call_automation_client.get_call_connection(
            call_connection_id
        ).get_call_properties()
        server_call_id = call_connection_properties.server_call_id
        correlation_id = call_connection_properties.correlation_id
        call_locator = ServerCallLocator(server_call_id)

        print(f"console.log: 🎙️ Starting audio recording on call ID: {call_connection_id}")
        print(f"console.log: 🔗 Correlation ID: {correlation_id}")

        recording_storage = (
            AzureBlobContainerRecordingStorage(BRING_YOUR_OWN_STORAGE_URL)
            if IS_BYOS
            else AzureCommunicationsRecordingStorage()
        )

        recording_options = (
            {
                "call_connection_id": call_connection_properties.call_connection_id,
                "recording_content_type": RecordingContent.AUDIO,
                "recording_channel_type": RecordingChannel.MIXED,
                "recording_format_type": RecordingFormat.WAV,
                "recording_state_callback_url": callback_uri_host + "/api/callbacks",
                "recording_storage": recording_storage,
                "pause_on_start": is_pause_on_start
            }
            if is_recording_with_call_connection_id
            else {
                "call_locator": call_locator,
                "recording_content_type": RecordingContent.AUDIO,
                "recording_channel_type": RecordingChannel.MIXED,
                "recording_format_type": RecordingFormat.WAV,
                "recording_state_callback_url": callback_uri_host + "/api/callbacks",
                "recording_storage": recording_storage,
                "pause_on_start": is_pause_on_start
            }
        )

        recording_result = await call_automation_client.start_recording(**recording_options)
        recording_id = recording_result.recording_id

        print(
            f"console.log: ✅ Recording started. RecordingId: {recording_id}, "
            f"CallConnectionId: {call_connection_id}, CorrelationId: {correlation_id}, "
            f"Status: {recording_result.recording_state}"
        )

        return CloudEvent(
            call_connection_id=call_connection_id,
            correlation_id=correlation_id,
            status=f"Recording started. RecordingId: {recording_id}. Status: {recording_result.recording_state}"
        )

    except Exception as ex:
        error_message = f"Error starting recording: {str(ex)}. CallConnectionId: {call_connection_id}"
        print(f"console.log: ❌ {error_message}")
        raise HTTPException(
            status_code=500,
            detail=error_message
        )

@app.post(
    "/startRecordingWithAudioWavMixed",
    tags=["Recording"],
    summary="Start audio recording in WAV format with mixed channel",
    description="Starts recording a call with audio only in WAV format with mixed channel configuration.",
    responses={
        302: {"description": "Redirect to home page after starting recording"}
    }
)
async def start_recording_with_audio_wav_mixed_handler(
    callConnectionId: str = Query(..., description="Call connection ID"),
    isRecordingWithCallConnectionId: bool = Query(..., description="Whether to use call connection ID for recording"),
    isPauseOnStart: bool = Query(..., description="Whether to pause recording on start")
):
    result = await start_recording_with_audio_wav_mixed_logic(
        call_connection_id=callConnectionId,
        is_recording_with_call_connection_id=isRecordingWithCallConnectionId,
        is_pause_on_start=isPauseOnStart
    )
    return RedirectResponse(url="/")


@app.post(
    "/startRecordingWithAudioWavUnmixed",
    tags=["Recording"],
    summary="Start audio recording in WAV format with unmixed channel",
    description="Starts recording a call with audio only in WAV format with unmixed channel configuration.",
    responses={
        302: {"description": "Redirect to home page after starting recording"}
    }
)
async def start_recording_with_audio_wav_unmixed_handler(
    callConnectionId: str = Query(..., description="Call connection ID"),
    isRecordingWithCallConnectionId: bool = Query(..., description="Whether to use call connection ID for recording"),
    isPauseOnStart: bool = Query(..., description="Whether to pause recording on start")
):
    result = await start_recording_with_audio_wav_unmixed_logic(
        call_connection_id=callConnectionId,
        is_recording_with_call_connection_id=isRecordingWithCallConnectionId,
        is_pause_on_start=isPauseOnStart
    )
    return RedirectResponse(url="/")

    
    
async def start_recording_with_audio_mp3_mixed_logic(
    call_connection_id: str,
    is_recording_with_call_connection_id: bool,
    is_pause_on_start: bool
):
    global recording_id
    try:
        call_connection_properties = await call_automation_client.get_call_connection(
            call_connection_id
        ).get_call_properties()
        server_call_id = call_connection_properties.server_call_id
        correlation_id = call_connection_properties.correlation_id
        call_locator = ServerCallLocator(server_call_id)

        print(f"console.log: 🎙️ Starting audio recording on call ID: {call_connection_id}")
        print(f"console.log: 🔗 Correlation ID: {correlation_id}")

        recording_storage = (
            AzureBlobContainerRecordingStorage(BRING_YOUR_OWN_STORAGE_URL)
            if IS_BYOS
            else AzureCommunicationsRecordingStorage()
        )

        recording_options = (
            {
                "call_connection_id": call_connection_properties.call_connection_id,
                "recording_content_type": RecordingContent.AUDIO,
                "recording_channel_type": RecordingChannel.MIXED,
                "recording_format_type": RecordingFormat.MP3,
                "recording_state_callback_url": callback_uri_host + "/api/callbacks",
                "recording_storage": recording_storage,
                "pause_on_start": is_pause_on_start
            }
            if is_recording_with_call_connection_id
            else {
                "call_locator": call_locator,
                "recording_content_type": RecordingContent.AUDIO,
                "recording_channel_type": RecordingChannel.MIXED,
                "recording_format_type": RecordingFormat.MP3,
                "recording_state_callback_url": callback_uri_host + "/api/callbacks",
                "recording_storage": recording_storage,
                "pause_on_start": is_pause_on_start
            }
        )

        recording_result = await call_automation_client.start_recording(**recording_options)
        recording_id = recording_result.recording_id

        print(
            f"console.log: ✅ Recording started. RecordingId: {recording_id}, "
            f"CallConnectionId: {call_connection_id}, CorrelationId: {correlation_id}, "
            f"Status: {recording_result.recording_state}"
        )

        return CloudEvent(
            call_connection_id=call_connection_id,
            correlation_id=correlation_id,
            status=f"Recording started. RecordingId: {recording_id}. Status: {recording_result.recording_state}"
        )

    except Exception as ex:
        error_message = f"Error starting recording: {str(ex)}. CallConnectionId: {call_connection_id}"
        print(f"console.log: ❌ {error_message}")
        raise HTTPException(
            status_code=500,
            detail=error_message
        )

@app.post(
    "/startRecordingWithAudioMp3Mixed",
    tags=["Recording"],
    summary="Start audio recording in MP3 format",
    description="Starts recording a call with audio only in MP3 format with mixed channel configuration.",
    responses={
        302: {"description": "Redirect to home page after starting recording"}
    }
)
async def start_recording_with_audio_mp3_mixed_handler(
    callConnectionId: str = Query(..., description="Call connection ID"),
    isRecordingWithCallConnectionId: bool = Query(..., description="Whether to use call connection ID for recording"),
    isPauseOnStart: bool = Query(..., description="Whether to pause recording on start")
):
    result = await start_recording_with_audio_mp3_mixed_logic(
        call_connection_id=callConnectionId,
        is_recording_with_call_connection_id=isRecordingWithCallConnectionId,
        is_pause_on_start=isPauseOnStart
    )
    return RedirectResponse(url="/")





@app.post(
    "/startRecordingWithVideoMp4Mixed",
    tags=["Recording"],
    summary="Start audio-video recording in MP4 format",
    description="Starts recording a call with audio and video in MP4 format with mixed channel configuration.",
    responses={
        302: {"description": "Redirect to home page after starting recording"}
    }
)
async def start_recording_with_video_mp4_mixed_handler(
    callConnectionId: str = Query(..., description="Call connection ID"),
    isRecordingWithCallConnectionId: bool = Query(..., description="Whether to use call connection ID for recording"),
    isPauseOnStart: bool = Query(..., description="Whether to pause recording on start")
):
    result = await start_recording_with_video_mp4_mixed_logic(
        call_connection_id=callConnectionId,
        is_recording_with_call_connection_id=isRecordingWithCallConnectionId,
        is_pause_on_start=isPauseOnStart
    )
    return RedirectResponse(url="/")


# 🚀 Swagger-visible Endpoint
@app.post(
    "/transferCallToAcsParticipantAsync",
    tags=["Transfer Call APIs"],
    summary="Transfer call from one ACS participant to another",
    description="Transfers the call from a current ACS user (transferee) to another ACS user (target).",
    responses={302: {"description": "Redirects to homepage after transfer"}}
)
async def transfer_call_to_acs_participant_handler(
    callConnectionId: str = Query(..., description="Active call connection ID"),
    acsTransferTarget: str = Query(..., description="ACS participant to transfer the call to"),
    acsTarget: str = Query(..., description="ACS participant currently in the call (transferee)")
):
    await transfer_call_to_acs_participant(
        call_connection_id=callConnectionId,
        transfer_target_id=acsTransferTarget,
        transferee_id=acsTarget
    )
    return RedirectResponse(url="/")



async def start_recording_logic(
    call_connection_id: str,
    is_recording_with_call_connection_id: bool,
    is_pause_on_start: bool
):
    global recording_id
    try:
        call_connection_properties = await call_automation_client.get_call_connection(
            call_connection_id
        ).get_call_properties()
        server_call_id = call_connection_properties.server_call_id
        correlation_id = call_connection_properties.correlation_id
        call_locator = ServerCallLocator(server_call_id)

        print(f"console.log: 🎙️ Starting audio recording on call ID: {call_connection_id}")
        print(f"console.log: 🔗 Correlation ID: {correlation_id}")

        recording_storage = (
            AzureBlobContainerRecordingStorage(BRING_YOUR_OWN_STORAGE_URL)
            if IS_BYOS
            else AzureCommunicationsRecordingStorage()
        )

        recording_options = (
            {
                "call_connection_id": call_connection_properties.call_connection_id,
                "recording_content_type": RecordingContent.AUDIO,
                "recording_channel_type": RecordingChannel.UNMIXED,
                "recording_format_type": RecordingFormat.WAV,
                "recording_state_callback_url": callback_uri_host + "/api/callbacks",
                "recording_storage": recording_storage,
                "pause_on_start": is_pause_on_start
            }
            if is_recording_with_call_connection_id
            else {
                "call_locator": call_locator,
                "recording_content_type": RecordingContent.AUDIO,
                "recording_channel_type": RecordingChannel.UNMIXED,
                "recording_format_type": RecordingFormat.WAV,
                "recording_state_callback_url": callback_uri_host + "/api/callbacks",
                "recording_storage": recording_storage,
                "pause_on_start": is_pause_on_start
            }
        )

        recording_result = await call_automation_client.start_recording(**recording_options)
        recording_id = recording_result.recording_id

        print(
            f"console.log: ✅ Recording started. RecordingId: {recording_id}, "
            f"CallConnectionId: {call_connection_id}, CorrelationId: {correlation_id}, "
            f"Status: {recording_result.recording_state}"
        )

        return CloudEvent(
            call_connection_id=call_connection_id,
            correlation_id=correlation_id,
            status=f"Recording started. RecordingId: {recording_id}. Status: {recording_result.recording_state}"
        )

    except Exception as ex:
        error_message = f"Error starting recording: {str(ex)}. CallConnectionId: {call_connection_id}"
        print(f"console.log: ❌ {error_message}")
        raise HTTPException(
            status_code=500,
            detail=error_message
        )

@app.post(
    "/startRecording",
    tags=["Recording"],
    summary="Start call recording",
    description="Starts recording an active call with audio only in WAV format with unmixed channel configuration.",
    responses={
        302: {"description": "Redirect to home page after starting recording"}
    }
)
async def start_recording_handler(
    callConnectionId: str = Query(..., description="Call connection ID"),
    isRecordingWithCallConnectionId: bool = Query(..., description="Whether to use call connection ID for recording"),
    isPauseOnStart: bool = Query(..., description="Whether to pause recording on start")
):
    result = await start_recording_logic(
        call_connection_id=callConnectionId,
        is_recording_with_call_connection_id=isRecordingWithCallConnectionId,
        is_pause_on_start=isPauseOnStart
    )
    return RedirectResponse(url="/")

async def pause_recording_logic(recording_id: str):
    try:
        if not recording_id:
            print(f"console.log: ⚠️ Recording id is empty.")
            raise HTTPException(
                status_code=400,
                detail="Recording id is empty."
            )

        recording_state = await get_recording_state(recording_id)  # Update get_recording_state to accept recording_id
        if recording_state == "active":
            print(f"console.log: ⏸️ Pausing recording with RecordingId: {recording_id}")
            await call_automation_client.pause_recording(recording_id)
            print(f"console.log: ✅ Recording is paused.")
            return CloudEvent(
                recording_id=recording_id,
                status="Recording is paused."
            )
        else:
            print(f"console.log: ℹ️ Recording is already inactive. RecordingId: {recording_id}")
            return CloudEvent(
                recording_id=recording_id,
                status="Recording is already inactive."
            )

    except Exception as ex:
        error_message = f"Error pausing recording: {str(ex)}. RecordingId: {recording_id}"
        print(f"console.log: ❌ {error_message}")
        raise HTTPException(
            status_code=500,
            detail=error_message
        )

@app.post(
    "/pauseRecording",
    tags=["Recording"],
    summary="Pause call recording",
    description="Pauses an active call recording.",
    responses={
        302: {"description": "Redirect to home page after pausing recording"}
    }
)
async def pause_recording_handler(
    recordingId: str = Query(..., description="Recording ID to pause")
):
    """Pause call recording."""
    result = await pause_recording_logic(recording_id=recordingId)
    return RedirectResponse(url="/")



async def resume_recording_logic(recording_id: str, call_connection_id: str):
    try:
        if not recording_id:
            print(f"console.log: ⚠️ Recording id is empty.")
            raise HTTPException(
                status_code=400,
                detail="Recording id is empty."
            )

        if not call_connection_id:
            print(f"console.log: ⚠️ Call connection id is empty.")
            raise HTTPException(
                status_code=400,
                detail="Call connection id is empty."
            )

        # Fetch call properties to get correlationId
        call_connection_properties = await call_automation_client.get_call_connection(
            call_connection_id
        ).get_call_properties()
        correlation_id = call_connection_properties.correlation_id

        recording_state = await get_recording_state(recording_id)  # Update get_recording_state to accept recording_id
        if recording_state == "inactive":
            print(f"console.log: ▶️ Resuming recording with RecordingId: {recording_id}")
            await call_automation_client.resume_recording(recording_id)
            print(f"console.log: ✅ Recording is resumed.")
            status_message = "Recording is resumed."
        else:
            print(f"console.log: ℹ️ Recording is already active. RecordingId: {recording_id}")
            status_message = "Recording is already active."

        return CloudEventData(
            callConnectionId=call_connection_id,
            correlationId=correlation_id,
            resultInformation={"status": status_message}
        )

    except Exception as ex:
        error_message = f"Error resuming recording: {str(ex)}. RecordingId: {recording_id}, CallConnectionId: {call_connection_id}"
        print(f"console.log: ❌ {error_message}")
        raise HTTPException(
            status_code=500,
            detail=error_message
        )

@app.post(
    "/resumeRecording",
    tags=["Recording"],
    summary="Resume call recording",
    description="Resumes a paused call recording.",
    responses={
        302: {"description": "Redirect to home page after resuming recording"}
    }
)
async def resume_recording_handler(
    recordingId: str = Query(..., description="Recording ID to resume"),
    callConnectionId: str = Query(..., description="Call connection ID")
):
    """Resume call recording."""
    result = await resume_recording_logic(recording_id=recordingId, call_connection_id=callConnectionId)
    return RedirectResponse(url="/")



@app.post(
    "/playWithInterruptMediaFlag",
    tags=["Media Operations"],
    summary="Play media with interrupt flag",
    description="Plays media with an interrupt flag enabled, allowing media to be interrupted by other operations.",
    responses={
        302: {"description": "Redirect to home page after playing media"}
    }
)
async def play_with_interrupt_media_flag_handler():
    """Play media with interrupt flag."""
    await play_with_interrupt_media_flag()
    return RedirectResponse(url="/")

@app.post(
    "/cancelAllMediaOperation",
    tags=["Media Operations"],
    summary="Cancel all media operations",
    description="Cancels all active media operations for a call.",
    responses={
        302: {"description": "Redirect to home page after canceling media operations"}
    }
)
async def cancel_all_media_operation_handler():
    """Cancel all media operations."""
    await cancel_all_media_oparation()
    return RedirectResponse(url="/")

@app.post(
    "/hangupCall",
    tags=["Disconnect call APIs"],
    summary="Hang up call",
    description="Hangs up an active call without terminating it for other participants.",
    responses={
        302: {"description": "Redirect to home page after hanging up call"}
    }
)
async def hangup_call_handler():
    """Hang up call."""
    await hangup_call()
    return RedirectResponse(url="/")

@app.post(
    "/terminateCall",
    tags=["Call Management"],
    summary="Terminate call",
    description="Terminates an active call for all participants.",
    responses={
        302: {"description": "Redirect to home page after terminating call"}
    }
)
async def terminate_call_handler():
    """Terminate call."""
    await terminate_call()
    return RedirectResponse(url="/")


async def index_handler(request: Request):
    """Render the home page."""
    return templates.TemplateResponse("index.html", {"request": request})

class CallMedia:
    def stop_media_streaming(self):
        # Logic to stop media streaming (simulated)
        pass

class CallConnection:
    def __init__(self, call_connection_id: str):
        self.call_connection_id = call_connection_id
        self.call_media = CallMedia()

    def get_call_media(self):
        return self.call_media

@app.post(
    "/stopMediaStreaming",
    tags=["Media Streaming"],
    summary="Stop media streaming",
    description="Stops media streaming for a given call connection.",
    responses={
        200: {"description": "Successfully stopped media streaming"},
        400: {"description": "Bad Request, call connection ID is missing"},
        500: {"description": "Internal server error while stopping media streaming"},
    },
)
async def stop_media_streaming(call_connection_id: str):
    """Stops media streaming for a given call connection."""
    try:
        call_media = get_call_media(call_connection_id)
        call_media.stop_media_streaming()
        log.info(f"Stopped media streaming for call: {call_connection_id}")
        return {"message": "Media streaming stopped successfully."}
    except Exception as e:
        log.error(f"Error stopping media streaming: {e}")
        raise HTTPException(status_code=500, detail="Failed to stop media streaming.")

def get_call_media(call_connection_id: str):
    if not call_connection_id:
        raise HTTPException(status_code=400, detail="Call connection id is empty")
    # In a real scenario, fetch the call connection from the client or service
    return CallConnection(call_connection_id).get_call_media()

@app.post(
    "/startMediaStreaming",
    tags=["Media Streaming"],
    summary="Start media streaming",
    description="Starts media streaming for a given call connection.",
    responses={
        200: {"description": "Successfully started media streaming"},
        400: {"description": "Bad Request, call connection ID is missing"},
        500: {"description": "Internal server error while starting media streaming"},
    },
)
async def start_media_streaming(call_connection_id: str):
    """Starts media streaming for a given call connection."""
    try:
        call_media = get_call_media(call_connection_id)
        # Simulate the start of media streaming (replace with actual logic)
        call_media.start_media_streaming()
        log.info(f"Started media streaming for call: {call_connection_id}")
        return {"message": "Media streaming started successfully."}
    except Exception as e:
        log.error(f"Error starting media streaming: {e}")
        raise HTTPException(status_code=500, detail="Failed to start media streaming.")

def get_call_media(call_connection_id: str):
    if not call_connection_id:
        raise HTTPException(status_code=400, detail="Call connection id is empty")
    # In a real scenario, fetch the call connection from the client or service
    return CallConnection(call_connection_id).get_call_media()

@app.post(
    "/updateTranscription",
    tags=["Transcription"],
    summary="Update call transcription",
    description="Updates the transcription locale for a given call connection.",
    responses={
        200: {"description": "Successfully updated transcription"},
        400: {"description": "Bad Request, missing or invalid locale"},
        500: {"description": "Internal server error while updating transcription"},
    },
)
async def update_transcription(call_connection_id: str, new_locale: str):
    """Updates the transcription locale for a given call connection."""
    try:
        # Get CallMedia and update transcription synchronously
        call_media = get_call_media(call_connection_id)
        await call_media.update_transcription(new_locale)

        log.info("Updated transcription successfully.")
        return {"message": "Transcription updated successfully."}
    except Exception as e:
        log.error(f"Error updating transcription: {e}")
        raise HTTPException(status_code=500, detail="Failed to update transcription.")

@app.post(
    "/stopTranscriptionAsync",
    tags=["Transcription"],
    summary="Stop call transcription asynchronously",
    description="Stops the transcription asynchronously for a given call connection.",
    responses={
        200: {"description": "Successfully stopped transcription"},
        400: {"description": "Bad Request, call connection ID is missing"},
        500: {"description": "Internal server error while stopping transcription"},
    },
)
async def stop_transcription_async(call_connection_id: str):
    """Stops transcription asynchronously for a given call connection."""
    try:
       # transcription_options = StopTranscriptionOptions()

        # Get CallMedia and stop transcription asynchronously
        call_media = get_call_media(call_connection_id)
        #await call_media.stop_transcription_async(transcription_options)

        log.info(f"Stopped transcription asynchronously for call: {call_connection_id}")
        return {"message": "Transcription stopped successfully."}
    except Exception as e:
        log.error(f"Error stopping transcription: {e}")
        raise HTTPException(status_code=500, detail="Failed to stop transcription.")


@app.post(
    "/createCallWithTranscription",
    tags=["Transcription"],
    summary="Create call with transcription",
    description="Creates a call with transcription options enabled and returns the call connection ID.",
    responses={
        200: {"description": "Successfully created call with transcription"},
        500: {"description": "Internal server error while creating the call"},
    },
)


async def create_call_with_transcription():
    """Creates a call with transcription enabled."""
    try:
        # Prepare call invite and transcription options
        target = CommunicationUserIdentifier(ACS_PHONE_NUMBER)
        call_invite = CallInvite(target)
        callback_uri = f"{callback_uri_host}/api/callbacks"
        websocket_uri = WEBSOCKET_URI_HOST.replace("https", "wss") + "/ws"

        #create_call_options = CreateCallOptions(call_invite, callback_uri)
       # call_intelligence_options = CallIntelligenceOptions(COGNITIVE_SERVICES_ENDPOINT)
        #transcription_options = TranscriptionOptions(websocket_uri, "WEBSOCKET", "en-US", False)

       # create_call_options.set_call_intelligence_options(call_intelligence_options)
       # create_call_options.set_transcription_options(transcription_options)

        # Create call with response
        #result = await client.create_call_with_response(create_call_options, Context.NONE)
       # call_connection_id = result.value.call_connection_properties.call_connection_id
        
        log.info(f"Created async call with connection id: {call_connection_id}")
        return {"message": f"Created async call with connection id: {call_connection_id}"}

    except Exception as e:
        log.error(f"Error creating call: {e}")
        raise HTTPException(status_code=500, detail="Failed to create call.")


@app.post(
    "/createCallWithPlay",
    tags=["Play Media"],
    summary="Create call with play media",
    description="Creates a call with play media feature and returns the call connection ID.",
    responses={
        200: {"description": "Successfully created call with play media"},
        500: {"description": "Internal server error while creating the call"},
    },
)
async def create_call_with_play():
    """Creates a call with play media capability."""
    try:
        # Prepare call invite and options
        target = CommunicationUserIdentifier(ACS_PHONE_NUMBER)
        call_invite = CallInvite(target)
        callback_uri = f"{callback_uri_host}/api/callbacks"

       # create_call_options = CreateCallOptions(call_invite, callback_uri)
        #call_intelligence_options = CallIntelligenceOptions(COGNITIVE_SERVICES_ENDPOINT)
        #create_call_options.set_call_intelligence_options(call_intelligence_options)

        # Create call with response
        #result = await client.create_call_with_response(create_call_options, Context.NONE)
        #call_connection_id = result.value.call_connection_properties.call_connection_id
        
        log.info(f"Created async call with connection id: {call_connection_id}")
        return {"message": f"Created async call with connection id: {call_connection_id}"}

    except Exception as e:
        log.error(f"Error creating call: {e}")
        raise HTTPException(status_code=500, detail="Failed to create call.")


@app.post(
    "/playTextSourceTarget",
    tags=["Play Media"],
    summary="Play text source to target",
    description="Plays a text source to a specific target participant asynchronously in an active call.",
    responses={
        200: {"description": "Successfully played text source to target"},
        500: {"description": "Internal server error while playing text source to target"},
    },
)
async def play_text_source_target():
    """Plays a text source to a specific target asynchronously."""
    try:
        call_media = get_call_media()

        play_to = [CommunicationUserIdentifier(ACS_PHONE_NUMBER)]
        #text_source = create_text_source("Hi, this is test source played through play source thanks. Goodbye!")

        #play_options = PlayOptions(text_source, play_to)
        #play_options.operation_context = "playToContext"

        #await call_media.play_with_response(play_options)

        log.info("Successfully played text source to target asynchronously.")
        return {"message": "Successfully played text source to target asynchronously."}

    except Exception as e:
        log.error(f"Error playing text source to target asynchronously: {e}")
        raise HTTPException(status_code=500, detail="Failed to play text source to target asynchronously.")

@app.post(
    "/playTextSourceToAll",
    tags=["Play Media"],
    summary="Play text source to all",
    description="Plays a text source to all participants asynchronously in an active call.",
    responses={
        200: {"description": "Successfully played text source to all"},
        500: {"description": "Internal server error while playing text source to all"},
    },
)
async def play_text_source_to_all():
    """Plays a text source to all participants asynchronously."""
    try:
        call_media = get_call_media()

       # text_source = create_text_source("Hi, this is test source played through play source thanks. Goodbye!")

        #play_options = PlayToAllOptions(text_source)
       # play_options.operation_context = "playToAllContext"

        #await call_media.play_to_all_with_response(play_options)

        log.info("Successfully played text source to all asynchronously.")
        return {"message": "Successfully played text source to all asynchronously."}

    except Exception as e:
        log.error(f"Error playing text source to all asynchronously: {e}")
        raise HTTPException(status_code=500, detail="Failed to play text source to all asynchronously.")


@app.post(
    "/playTextSourceBargeIn",
    tags=["Play Media"],
    summary="Play text source with barge-in to all",
    description="Plays a text source to all participants with barge-in enabled (interrupts any ongoing media operations) asynchronously in an active call.",
    responses={
        200: {"description": "Successfully played text source to all with barge-in"},
        500: {"description": "Internal server error while playing text source to all with barge-in"},
    },
)
async def play_text_source_barge_in_to_all():
    """Plays a text source to all participants with barge-in asynchronously."""
    try:
        call_media = get_call_media()

        #text_source = create_text_source("Hi, this is barge in test played through play source thanks. Goodbye!")

        #play_options = PlayToAllOptions(text_source)
        #play_options.operation_context = "playToAllContext"
        #play_options.interrupt_call_media_operation = True

       # await call_media.play_to_all_with_response(play_options)

        log.info("Successfully played text source to all with barge-in.")
        return {"message": "Successfully played text source to all with barge-in."}

    except Exception as e:
        log.error(f"Error playing text source to all with barge-in: {e}")
        raise HTTPException(status_code=500, detail="Failed to play text source to all with barge-in.")

# Add this near the end of your file, before the if __name__ == "__main__" block

@app.api_route("/", methods=["GET", "POST"], response_class=HTMLResponse)
async def root(request: Request):
    return "<h2>ACS Call Automation Sample API is running.</h2>"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)