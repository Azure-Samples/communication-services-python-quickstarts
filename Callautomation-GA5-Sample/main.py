import base64
from urllib import request
from fastapi import Body, FastAPI, HTTPException, Query, Request, Response, requests
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from urllib.parse import urlencode, urljoin, urlparse, urlunparse
from flask import render_template
from pydantic import BaseModel, Field
from typing import List, Optional
from azure.eventgrid import EventGridEvent, SystemEventNames
from azure.communication.callautomation import (
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
    ServerCallLocator,
    MediaStreamingOptions,
    StreamingTransportType,
    MediaStreamingAudioChannelType,
    AudioFormat,
    MediaStreamingContentType,
    TranscriptionOptions,
    MicrosoftTeamsUserIdentifier,
    TeamsExtensionUserIdentifier,
    MicrosoftTeamsAppIdentifier,
    TeamsPhoneCallDetails,
    TeamsPhoneCallerDetails
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

ACS_CONNECTION_STRING = ""
COGNITIVE_SERVICES_ENDPOINT = ""
ACS_PHONE_NUMBER = ""
# Target phone number you want to receive the call
TARGET_PHONE_NUMBER = ""
PARTICIPANT_PHONE_NUMBER = ""
TARGET_COMMUNICATION_USER = ""
PARTICIPANT_COMMUNICATION_USER = ""

WEBSOCKET_URI_HOST = ""

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
IS_CallConnectionId = True
IS_PAUSE_ON_START = False
IS_ANSWERED = True

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

# class TextSource(BaseModel):
#     text: str
#     voice_name: str = "en-US-NancyNeural"
#     source_locale: str = "en-US"
#     voice_kind: str = "MALE"

# class PlayOptions(BaseModel):
#     ssml_source: TextSource
#     operation_context: str
#     async_option: bool

class TargetType(str):
    PSTN = "PSTN"
    ACS = "ACS"
    TEAMS = "TEAMS"
    ALL = "ALL"

# Initialize FastAPI app with Swagger UI customization
app = FastAPI(
    title="ACS Contoso GA5-Python",
    description="API for managing calls, media, and recordings using Azure Communication Services.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)
# class CallMedia:
#     def stop_media_streaming(self):
#         # Logic to stop media streaming (simulated)
#         pass

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
content_location = ""
metadata_location = ""
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
CALLBACK_EVENTS_URI = f"{callback_uri_host}/api/callbacks"


def init_client():
    # Dummy client initializer
    log.info("Client initialized with ACS Connection String: %s", acs_connection_string)
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
        # # Validate and set values
        # configuration.acs_connection_string = configuration_request.acs_connection_string.strip() or \
        #     (_ for _ in ()).throw(ValueError("AcsConnectionString is required"))
        # configuration.cognitive_service_endpoint = configuration_request.cognitive_service_endpoint.strip() or \
        #     (_ for _ in ()).throw(ValueError("CognitiveServiceEndpoint is required"))
        # configuration.acs_phone_number = configuration_request.acs_phone_number.strip() or \
        #     (_ for _ in ()).throw(ValueError("AcsPhoneNumber is required"))
        # configuration.callback_uri_host = configuration_request.callback_uri_host.strip() or \
        #     (_ for _ in ()).throw(ValueError("CallbackUriHost is required"))
        # configuration.websocket_uri_host = configuration_request.websocket_uri_host.strip() or \
        #     (_ for _ in ()).throw(ValueError("WebsocketUriHost is required"))

        # # Assign to global variables
        # acs_connection_string = configuration.acs_connection_string
        # cognitive_services_endpoint = configuration.cognitive_service_endpoint
        # acs_phone_number = configuration.acs_phone_number
        # callback_uri_host = configuration.callback_uri_host
        # websocket_uri_host = configuration.websocket_uri_host

        client = init_client()

        log.info("Initialized call automation client.")
        return {"message": "Configuration set successfully. Initialized call automation client."}

    except Exception as e:
        log.error(f"Error configuring: {e}")
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

async def create_call_TPE(userId: str, tenantId: str, resourceId: str, teamsAppId: str):
        tpe_target = TeamsExtensionUserIdentifier(user_id=userId, tenant_id=tenantId, resource_id=resourceId)

        media_streaming_options = MediaStreamingOptions(
        transport_url= WEBSOCKET_URI_HOST,
        # transport_url= "https://abc.com",
        transport_type= StreamingTransportType.WEBSOCKET,
        content_type= MediaStreamingContentType.AUDIO,
        audio_channel_type= MediaStreamingAudioChannelType.UNMIXED,
        audio_format=AudioFormat.PCM24_K_MONO,
        enable_bidirectional= False,
        enable_dtmf_tones=False,
        start_media_streaming= False
        )

        transcription_options = TranscriptionOptions(
            # transport_url= "https://abc.com",
            transport_url= WEBSOCKET_URI_HOST,
            transport_type= StreamingTransportType.WEBSOCKET,
            locale="en-us",
            start_transcription=False
        )
        call_connection_properties = await call_automation_client.create_call(
            tpe_target,
            CALLBACK_EVENTS_URI,
            cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT,
            teams_app_source= MicrosoftTeamsAppIdentifier(app_id=teamsAppId),
            media_streaming=media_streaming_options,
            transcription=transcription_options
        )

async def create_call_acs():
        acs_target = CommunicationUserIdentifier(TARGET_COMMUNICATION_USER)

        media_streaming_options = MediaStreamingOptions(
        transport_url= WEBSOCKET_URI_HOST,
        transport_type= StreamingTransportType.WEBSOCKET,
        content_type= MediaStreamingContentType.AUDIO,
        audio_channel_type= MediaStreamingAudioChannelType.UNMIXED,
        audio_format=AudioFormat.PCM24_K_MONO,
        enable_bidirectional= False,
        enable_dtmf_tones= True,
        start_media_streaming= True
    )
        
    #     transcription_options = TranscriptionOptions(
    #     transport_url= WEBSOCKET_URI_HOST,
    #     transport_type= StreamingTransportType.WEBSOCKET,
    #     locale="en-us",
    #     start_transcription=True
    # )


        call_connection_properties = await call_automation_client.create_call(
            acs_target,
            CALLBACK_EVENTS_URI,
            cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT,
            media_streaming= media_streaming_options,
            # transcription=transcription_options
        )


# Helper functions (unchanged from original code)
async def create_call():
    is_acs_user_target = False
    if is_acs_user_target:
        acs_target = CommunicationUserIdentifier(TARGET_COMMUNICATION_USER)
        call_connection_properties = await call_automation_client.create_call(
            acs_target,
            CALLBACK_EVENTS_URI,
            cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT
        )
    else:
        pstn_target = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
        source_caller = PhoneNumberIdentifier(ACS_PHONE_NUMBER)
        call_connection_properties = await call_automation_client.create_call(
            pstn_target,
            CALLBACK_EVENTS_URI,
            cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT,
            source_caller_id_number=source_caller
        )
    logger.info("Created call with Correlation id: - %s", call_connection_properties.correlation_id)



async def create_group_call(userId: str, enable_loopback_audio: bool):
    """
    Creates a call to a single participant.
    
    Args:
        target (str): A single target identifier (ACS ID or PSTN phone number).
    """
    # if not target or not isinstance(target, str):
    #     raise ValueError("Target identifier must be a non-empty string.")

    # logger.info(f"Processing target: {target}")

    # if target.startswith("+") and target[1:].isdigit():
    #     invite = CallInvite(PhoneNumberIdentifier(target))
    # elif target.startswith("8:acs:") and len(target) > 6:
    #     invite = CallInvite(CommunicationUserIdentifier(target))
    # else:
    #     raise ValueError(f"Invalid target format: {target}")
    source_caller = PhoneNumberIdentifier(ACS_PHONE_NUMBER)
    target = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
    AcsTarget = CommunicationUserIdentifier(userId)
    # invite = CallInvite(
    #     target=target, source_caller_id_number=source_caller)
    
    media_streaming_options = MediaStreamingOptions(
        transport_url= WEBSOCKET_URI_HOST,
        transport_type= StreamingTransportType.WEBSOCKET,
        content_type= MediaStreamingContentType.AUDIO,
        audio_channel_type= MediaStreamingAudioChannelType.UNMIXED,
        audio_format=AudioFormat.PCM16_K_MONO,
        start_media_streaming= False
    )

    transcription_options = TranscriptionOptions(
        # transport_url= "https://abc.com",
        transport_url= WEBSOCKET_URI_HOST,
        transport_type= StreamingTransportType.WEBSOCKET,
        locale="en-us",
        start_transcription=False
    )

    call_connection_properties = await call_automation_client.create_group_call(
        [target, AcsTarget],                          # single CallInvite object
        CALLBACK_EVENTS_URI,            # callback_url
        source_caller_id_number=source_caller,
        cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT,
        media_streaming_options = media_streaming_options,
        transcription=transcription_options,
        enable_loopback_audio=enable_loopback_audio,
    )

    logger.info("Created call with connection id: %s", call_connection_properties.call_connection_id)
    logger.info("Correlation ID: %s", call_connection_properties.correlation_id)


async def connect_call(roomId: str):

    media_streaming_options = MediaStreamingOptions(
        transport_url= WEBSOCKET_URI_HOST,
        # transport_url= "https://abc.com",
        transport_type= StreamingTransportType.WEBSOCKET,
        content_type= MediaStreamingContentType.AUDIO,
        audio_channel_type= MediaStreamingAudioChannelType.UNMIXED,
        audio_format=AudioFormat.PCM24_K_MONO,
        enable_bidirectional= False,
        enable_dtmf_tones=False,
        start_media_streaming= False
    )

    transcription_options = TranscriptionOptions(
        # transport_url= "https://abc.com",
        transport_url= WEBSOCKET_URI_HOST,
        transport_type= StreamingTransportType.WEBSOCKET,
        locale="en-us",
        start_transcription=False
    )

    call_connection_result = await call_automation_client.connect_call(
        room_id=roomId,
        # group_call_id="e168bd6f-fa31-4fbb-bf94-f69cf34fb217",
        # server_call_id="aHR0cHM6Ly9hcGkuZmxpZ2h0cHJveHkuc2t5cGUuY29tL2FwaS92Mi9jcC9jb252LW1hc28tMDMtcHJvZC1ha3MuY29udi5za3lwZS5jb20vY29udi9XOUZITFM4MUJrS29OS3hkY0tLMXRnP2k9MTAtMTI4LTk3LTE5NyZlPTYzODg2NjQzMjI3NzU4Mjc4OQ",
        callback_url=CALLBACK_EVENTS_URI,
        cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT,
        media_streaming=media_streaming_options,
        transcription=transcription_options,
        operation_context="connectCallContext"
    )
    logger.info("Connect call Correlation ID: %s", call_connection_result.correlation_id)

def get_choices():
    choices = [
        RecognitionChoice(label=CONFIRM_CHOICE_LABEL, phrases=["Confirm", "First", "One"], tone=DtmfTone.ONE),
        RecognitionChoice(label=CANCEL_CHOICE_LABEL, phrases=["Cancel", "Second", "Two"], tone=DtmfTone.TWO)
    ]
    return choices

async def play_recognize_choice():
    text_source = TextSource(text=RECOGNITION_PROMPT, voice_name="en-US-NancyNeural")
    file_source = FileSource(url=MAIN_MENU_PROMPT_URI)
    ssml_text = SsmlSource(ssml_text=SSML_INTERRUPT_TEXT)
    play_sources = [text_source, ssml_text]
    await call_automation_client.get_call_connection(call_connection_id).start_recognizing_media(
        input_type=RecognizeInputType.CHOICES,
        target_participant=PhoneNumberIdentifier(TARGET_PHONE_NUMBER),
        choices=get_choices(),
        play_prompt=text_source,
        interrupt_prompt=False,
        initial_silence_timeout=10,
        operation_context="choiceContext",
        operation_callback_url=CALLBACK_EVENTS_URI
    )

async def play_recognize_speech():
    text_source = TextSource(text=RECOGNITION_PROMPT, voice_name="en-US-NancyNeural")
    file_source = FileSource(url=MAIN_MENU_PROMPT_URI)
    ssml_text = SsmlSource(ssml_text=SSML_INTERRUPT_TEXT)
    play_sources = [text_source, ssml_text]
    await call_automation_client.get_call_connection(call_connection_id).start_recognizing_media(
        input_type=RecognizeInputType.SPEECH,
        target_participant=PhoneNumberIdentifier(TARGET_PHONE_NUMBER),
        choices=get_choices(),
        play_prompt=play_sources,
        interrupt_prompt=False,
        initial_silence_timeout=10,
        operation_context="choiceContext",
        operation_callback_url=CALLBACK_EVENTS_URI
    )

async def play_recognize_speech_or_dtmf():
    text_source = TextSource(text=RECOGNITION_PROMPT, voice_name="en-US-NancyNeural")
    file_source = FileSource(url=MAIN_MENU_PROMPT_URI)
    ssml_text = SsmlSource(ssml_text=SSML_INTERRUPT_TEXT)
    play_sources = [text_source, ssml_text]
    await call_automation_client.get_call_connection(call_connection_id).start_recognizing_media(
        input_type=RecognizeInputType.SPEECH_OR_DTMF,
        target_participant=PhoneNumberIdentifier(TARGET_PHONE_NUMBER),
        choices=get_choices(),
        play_prompt=play_sources,
        interrupt_prompt=False,
        initial_silence_timeout=10,
        operation_context="choiceContext",
        operation_callback_url=CALLBACK_EVENTS_URI,
        dtmf_max_tones_to_collect= 2,
    )

async def play_recognize_dtmf():
    text_source = TextSource(text=RECOGNITION_PROMPT, voice_name="en-US-NancyNeural")
    # file_source = FileSource(url=MAIN_MENU_PROMPT_URI)
    ssml_text = SsmlSource(ssml_text=SSML_INTERRUPT_TEXT)
    play_sources = [text_source, ssml_text]
    await call_automation_client.get_call_connection(call_connection_id).start_recognizing_media(
        input_type=RecognizeInputType.DTMF,
        target_participant=PhoneNumberIdentifier(TARGET_PHONE_NUMBER),
        choices=get_choices(),
        play_prompt=play_sources,
        interrupt_prompt=False,
        initial_silence_timeout=10,
        operation_context="choiceContext",
        dtmf_max_tones_to_collect=2
    )

async def play_media():
    is_play_to_all = True
    text_source = TextSource(text=PLAY_PROMPT, voice_name="en-US-NancyNeural")
    file_source = FileSource(url=MAIN_MENU_PROMPT_URI)
    ssml_text = SsmlSource(ssml_text=SSML_PLAY_TEXT)
    target = get_communication_target()
    play_sources = [text_source]
    if is_play_to_all:
        await call_automation_client.get_call_connection(call_connection_id).play_media_to_all(
            play_source=play_sources,
            operation_context="playToAllContext",
            loop=False,
            operation_callback_url=CALLBACK_EVENTS_URI,
            interrupt_call_media_operation=False
        )
    else:
        await call_automation_client.get_call_connection(call_connection_id).play_media(
            play_source=play_sources,
            play_to=[target],
            operation_context="playToTarget",
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
        await call_automation_client.stop_recording(recording_id)
        logger.info("Recording is stopped.") 
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

):
    await stop_recording()
    return RedirectResponse(url="/")



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
    # file_source = FileSource(url=MAIN_MENU_PROMPT_URI)
    target = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
    # target = CommunicationUserIdentifier(TARGET_COMMUNICATION_USER)
    await call_automation_client.get_call_connection(call_connection_id).hold(
        target_participant=target,
        play_source=text_source,
        operation_context="HoldUserContext"
    )

async def hold_tpe_participant(userId: str, tenantId: str, resourceId: str):
    text_source = TextSource(text=HOLD_PROMPT, voice_name="en-US-NancyNeural")
    # file_source = FileSource(url=MAIN_MENU_PROMPT_URI)
    # target = TeamsExtensionUserIdentifier(user_id=userId, tenant_id=tenantId, resource_id=resourceId)
    # await call_automation_client.get_call_connection(call_connection_id).hold(
    #     target_participant=target,
    #     play_source=text_source,
    #     operation_context="HoldUserContext"
    # )
    # time.sleep(5)
    # result = await get_participant(target)
    # logger.info("Participant:--> %s", result.identifier.raw_id)
    # logger.info("Is participant on hold:--> %s", result.is_on_hold)

async def unhold_participant():
    target = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
    await call_automation_client.get_call_connection(call_connection_id).unhold(
        target_participant=target,
        operation_context="UnholdUserContext"
    )

# async def unhold_tpe_participant(userId: str, tenantId: str, resourceId: str):
    # target = TeamsExtensionUserIdentifier(user_id=userId, tenant_id=tenantId, resource_id=resourceId)
    # await call_automation_client.get_call_connection(call_connection_id).unhold(
    #     target_participant=target,
    #     operation_context="UnholdUserContext"
    # )
    # time.sleep(5)
    # result = await get_participant(target)
    # logger.info("Participant:--> %s", result.identifier.raw_id)
    # logger.info("Is participant on hold:--> %s", result.is_on_hold)

async def play_with_interrupt_media_flag(isInterrupt1: bool, isInterrupt2: bool):
    text_source = TextSource(text=INTERRUPT_PROMPT, voice_name="en-US-NancyNeural")
    file_source = FileSource(url=MAIN_MENU_PROMPT_URI)
    ssml_text = SsmlSource(ssml_text=SSML_INTERRUPT_TEXT)
    play_sources = [text_source, file_source, ssml_text]
    call_connection = call_automation_client.get_call_connection(call_connection_id)
    await call_connection.play_media_to_all(
        play_source=play_sources,
        loop=False,
        operation_context="interruptMediaContext",
        operation_callback_url=CALLBACK_EVENTS_URI,
        interrupt_call_media_operation=isInterrupt1
    )
    await call_connection.play_media_to_all(
        play_source=text_source,
        loop=False,
        operation_context="interruptMediaContext",
        operation_callback_url=CALLBACK_EVENTS_URI,
        interrupt_call_media_operation=isInterrupt2
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
    logger.info("Participant: %s", participant.identifier.raw_id)
    logger.info("Is participant muted: %s", participant.is_muted)
    logger.info("Is participant on hold: %s", participant.is_on_hold)
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

async def hangup_call(is_for_everyone: bool):
    await call_automation_client.get_call_connection(call_connection_id).hang_up(is_for_everyone)

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

def get_call_properties():
    call_properties = call_automation_client.get_call_connection(call_connection_id).get_call_properties()
    return call_properties


# 1. API (Callbacks)
@app.post(
    "/api/callbacks",
    tags=["Call Management"],
    summary="Handle callback events for calls",
    description="Processes callback events from Azure Communication Services for call-related events.",
    responses={
        200: {"description": "Callback events processed successfully"}
    }
)
# 2. Handler (Callbacks)
async def callback_events_handler(request: Request):
    """Handle callback events for calls."""
    try:
        await process_callback_events(request)
        return Response(status_code=200)
    except Exception as e:
        print(f"Error processing callback events: {str(e)}")
        return Response(status_code=500)

# 3. Function (Callbacks)
async def process_callback_events(request: Request):
    global call_connection_id
    event_data = await request.json()
    for event_dict in event_data:
        event = CloudEvent.from_dict(event_dict)
        call_connection_id = event.data["callConnectionId"]
        print(f"{event.type} event received for call connection id: {call_connection_id}")
        call_connection_client = call_automation_client.get_call_connection(call_connection_id)

        if event.type == "Microsoft.Communication.CallConnected":
            print(f"Received CallConnected event for connection id: {call_connection_id}")
            print(f"CORRELATION ID: - {event.data['correlationId']}")
            print(f"CALL CONNECTION ID: --> {call_connection_id}")
            call_properties = await get_call_properties()
            media_streaming_subscription = call_properties.media_streaming_subscription
            print(f"Media Streaming state: --> {media_streaming_subscription.state}")
            transcription_subscription = call_properties.transcription_subscription
            print(f"Transcription state: --> {transcription_subscription.state}")
        elif event.type == "Microsoft.Communication.MediaStreamingStarted":
            
            print(f"Received Media Streaming Started event.")
            operation_context = event.data.get('operationContext')
            print(f"Operation Context: {operation_context if operation_context is not None else 'N/A'}")
            mediaStreamingUpdate = event.data['mediaStreamingUpdate']
            # print(f"Operation Context: - {event.data['operationContext']}")
            # print(f"Content Type: - {mediaStreamingUpdate["contentType"]}")
            # print(f"Media Streaming Status: - {mediaStreamingUpdate["mediaStreamingStatus"]}")
            # print(f"Media streaming status details: - {mediaStreamingUpdate["mediaStreamingStatusDetails"]}")
        elif event.type == "Microsoft.Communication.MediaStreamingStopped":
            print(f"Received Media Streaming stopped event.")
            stop_operation_context = event.data.get('operationContext')
            print(f"Operation Context: {stop_operation_context if stop_operation_context is not None else 'N/A'}")
            mediaStreamingUpdate = event.data['mediaStreamingUpdate']
            # print(f"Operation Context: - {event.data['operationContext']}")
            # print(f"Content Type: - {mediaStreamingUpdate["contentType"]}")
            # print(f"Media Streaming Status: - {mediaStreamingUpdate["mediaStreamingStatus"]}")
            # print(f"Media streaming status details: - {mediaStreamingUpdate["mediaStreamingStatusDetails"]}")
            
        elif event.type == "Microsoft.Communication.MediaStreamingFailed":
            print(f"Received Media Streaming failed event.")
            resultInformation = event.data['resultInformation']
            print(f"message: - {resultInformation['message']}")
            print(f"code: - {resultInformation['code']}")
            print(f"subCode: - {resultInformation['subCode']}")
        elif event.type == "Microsoft.Communication.ConnectFailed":
            print(f"Received ConnectFailed event for connection id: {call_connection_id}")
            print(f"Correlation Id: {event.data['correlationId']}")
            result_information = event.data["resultInformation"]
            print(f"Encountered error during connect, message={result_information['message']}, code={result_information['code']}, subCode={result_information['subCode']}")

        elif event.type == "Microsoft.Communication.TranscriptionStarted":
            print(f"Received TranscriptionStarted event.")
            operation_context = event.data.get('operationContext')
            print(f"Operation Context: {operation_context if operation_context is not None else 'N/A'}")
            transcriptionUpdate = event.data['transcriptionUpdate']
            # print(f"Transcription status: - {transcriptionUpdate["transcriptionStatus"]}")
            # print(f"Transcription status details: - {transcriptionUpdate["transcriptionStatusDetails"]}")
             
        elif event.type == "Microsoft.Communication.TranscriptionStopped":
                
            print(f"Received TranscriptionStopped event.")
            operation_context = event.data.get('operationContext')
            print(f"Operation Context: {operation_context if operation_context is not None else 'N/A'}")
            transcriptionUpdate = event.data['transcriptionUpdate']
            # print(f"Transcription status: - {transcriptionUpdate["transcriptionStatus"]}")
            # print(f"Transcription status details: - {transcriptionUpdate["transcriptionStatusDetails"]}")
                     
        elif event.type == "Microsoft.Communication.TranscriptionUpdated":
            print(f"Received TranscriptionUpdated event.")
            operation_context = event.data.get('operationContext')
            print(f"Operation Context: {operation_context if operation_context is not None else 'N/A'}")
            transcriptionUpdate = event.data['transcriptionUpdate']
            # print(f"Transcription status: - {transcriptionUpdate["transcriptionStatus"]}")
            # print(f"Transcription status details: - {transcriptionUpdate["transcriptionStatusDetails"]}")
        elif event.type == "Microsoft.Communication.TranscriptionFailed":
            print(f"Received TranscriptionFailed event.")
            resultInformation = event.data['resultInformation']
            print(f"message: - {resultInformation['message']}")
            print(f"code: - {resultInformation['code']}")
            print(f"subCode: - {resultInformation['subCode']}")

        elif event.type == "Microsoft.Communication.AddParticipantSucceeded":
            print(f"Received AddParticipantSucceeded event for connection id: {call_connection_id}")

        elif event.type == "Microsoft.Communication.RecognizeCompleted":
            print(f"Received RecognizeCompleted event for connection id: {call_connection_id}")
            if event.data["recognitionType"] == "dtmf":
                tones = event.data["dtmfResult"]["tones"]
                print(f"Recognition completed, tones={tones}, context={event.data['operationContext']}")
            elif event.data["recognitionType"] == "choices":
                label_detected = event.data["choiceResult"]["label"]
                phrase_detected = event.data["choiceResult"]["recognizedPhrase"]
                languageIdentified = event.data["choiceResult"]["languageIdentified"]
                sentiment = event.data["choiceResult"]["sentimentAnalysisResult"]["sentiment"]
                print(f"Recognition completed, labelDetected={label_detected}, phraseDetected={phrase_detected}, context={event.data['operationContext']}")
                print(f"language Identified={languageIdentified}")
                print(f"sentiment={sentiment}")
            elif event.data["recognitionType"] == "speech":
                text = event.data["speechResult"]["speech"]
                languageIdentified = event.data["speechResult"]["languageIdentified"]
                sentiment = event.data["speechResult"]["sentimentAnalysisResult"]["sentiment"]
                print(f"Recognition completed, text={text}, context={event.data['operationContext']}")
                print(f"language Identified={languageIdentified}")
                print(f"sentiment={sentiment}")
            else:
                print(f"Recognition completed: data={event.data}")

        elif event.type == "Microsoft.Communication.RecognizeFailed":
            print(f"Received RecognizeFailed event for connection id: {call_connection_id}")
            if "operationContext" in event.data:
                print(f"Operation context --> {event.data['operationContext']}")
            result_information = event.data["resultInformation"]
            print(f"Encountered error during Recognize, message={result_information['message']}, code={result_information['code']}, subCode={result_information['subCode']}")
            print(f"Play failed source index --> {event.data.get('failedPlaySourceIndex', 'N/A')}")

        elif event.type == "Microsoft.Communication.PlayCompleted":
            print(f"Received PlayCompleted event for connection id: {call_connection_id}")
            if "operationContext" in event.data:
                print(f"Operation context --> {event.data['operationContext']}")

        elif event.type == "Microsoft.Communication.PlayFailed":
            print(f"Received PlayFailed event for connection id: {call_connection_id}")
            if "operationContext" in event.data:
                print(f"Operation context --> {event.data['operationContext']}")
            result_information = event.data["resultInformation"]
            print(f"Encountered error during play, message={result_information['message']}, code={result_information['code']}, subCode={result_information['subCode']}")
            print(f"Play failed source index --> {event.data.get('failedPlaySourceIndex', 'N/A')}")

        elif event.type == "Microsoft.Communication.ContinuousDtmfRecognitionToneReceived":
            print(f"Received ContinuousDtmfRecognitionToneReceived event for connection id: {call_connection_id}")
            print(f"Tone received: --> {event.data['tone']}")
            print(f"Sequence Id: --> {event.data['sequenceId']}")

        elif event.type == "Microsoft.Communication.ContinuousDtmfRecognitionToneFailed":
            print(f"Received ContinuousDtmfRecognitionToneFailed event for connection id: {call_connection_id}")
            if "operationContext" in event.data:
                print(f"Operation context --> {event.data['operationContext']}")
            result_information = event.data["resultInformation"]
            print(f"Encountered error: message={result_information['message']}, code={result_information['code']}, subCode={result_information['subCode']}")

        elif event.type == "Microsoft.Communication.ContinuousDtmfRecognitionStopped":
            print(f"Received ContinuousDtmfRecognitionStopped event for connection id: {call_connection_id}")

        elif event.type == "Microsoft.Communication.SendDtmfTonesCompleted":
            print(f"Received SendDtmfTonesCompleted event for connection id: {call_connection_id}")

        elif event.type == "Microsoft.Communication.SendDtmfTonesFailed":
            print(f"Received SendDtmfTonesFailed event for connection id: {call_connection_id}")
            result_information = event.data["resultInformation"]
            print(f"Encountered error: message={result_information['message']}, code={result_information['code']}, subCode={result_information['subCode']}")

        elif event.type == "Microsoft.Communication.RemoveParticipantSucceeded":
            print(f"Received RemoveParticipantSucceeded event for connection id: {call_connection_id}")

        elif event.type == "Microsoft.Communication.RemoveParticipantFailed":
            print(f"Received RemoveParticipantFailed event for connection id: {call_connection_id}")
            result_information = event.data["resultInformation"]
            print(f"Encountered error: message={result_information['message']}, code={result_information['code']}, subCode={result_information['subCode']}")

        elif event.type == "Microsoft.Communication.HoldFailed":
            print(f"Received HoldFailed event for connection id: {call_connection_id}")
            result_information = event.data["resultInformation"]
            print(f"Encountered error during Hold, message={result_information['message']}, code={result_information['code']}, subCode={result_information['subCode']}")

        elif event.type == "Microsoft.Communication.PlayStarted":
            print(f"Received PlayStarted event for connection id: {call_connection_id}")

        elif event.type == "Microsoft.Communication.PlayCanceled":
            print(f"Received PlayCanceled event for connection id: {call_connection_id}")
            if "operationContext" in event.data:
                print(f"Operation context --> {event.data['operationContext']}")

        elif event.type == "Microsoft.Communication.RecognizeCanceled":
            print(f"Received RecognizeCanceled event for connection id: {call_connection_id}")
            if "operationContext" in event.data:
                print(f"Operation context --> {event.data['operationContext']}")

        elif event.type == "Microsoft.Communication.RecordingStateChanged":
            print(f"Received RecordingStateChanged event for connection id: {call_connection_id}")

        elif event.type == "Microsoft.Communication.CallTransferAccepted":
            print(f"Received CallTransferAccepted event for connection id: {call_connection_id}")

        elif event.type == "Microsoft.Communication.CallTransferFailed":
            print(f"Received CallTransferFailed event for connection id: {call_connection_id}")
            if "operationContext" in event.data:
                print(f"Operation context --> {event.data['operationContext']}")
            result_information = event.data["resultInformation"]
            print(f"Encountered error: message={result_information['message']}, code={result_information['code']}, subCode={result_information['subCode']}")

        elif event.type == "Microsoft.Communication.AddParticipantFailed":
            print(f"Received AddParticipantFailed event for connection id: {call_connection_id}")
            if "operationContext" in event.data:
                print(f"Operation context --> {event.data['operationContext']}")
            result_information = event.data["resultInformation"]
            print(f"Encountered error: message={result_information['message']}, code={result_information['code']}, subCode={result_information['subCode']}")

        elif event.type == "Microsoft.Communication.CancelAddParticipantSucceeded":
            print(f"Received CancelAddParticipantSucceeded event for connection id: {call_connection_id}")
            print(f"Operation context --> {event.data['operationContext']}")

        elif event.type == "Microsoft.Communication.CancelAddParticipantFailed":
            print(f"Received CancelAddParticipantFailed event for connection id: {call_connection_id}")
            if "operationContext" in event.data:
                print(f"Operation context --> {event.data['operationContext']}")
            result_information = event.data["resultInformation"]
            print(f"Encountered error: message={result_information['message']}, code={result_information['code']}, subCode={result_information['subCode']}")

        elif event.type == "Microsoft.Communication.CreateCallFailed":
            print(f"Received CreateCallFailed event for connection id: {call_connection_id}")
            if "operationContext" in event.data:
                print(f"Operation context --> {event.data['operationContext']}")
            result_information = event.data["resultInformation"]
            print(f"Encountered error: message={result_information['message']}, code={result_information['code']}, subCode={result_information['subCode']}")

        elif event.type == "Microsoft.Communication.CallDisconnected":
            print(f"Received CallDisconnected event for connection id: {call_connection_id}")
            print(f"CORRELATION ID: - {event.data['correlationId']}")
            print(f"CALL CONNECTION ID: --> {call_connection_id}")

from starlette.responses import RedirectResponse as redirect

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
        # content_location = "https://as-storage.asm.skype.com/v1/objects/0-jhb-d4-98459381f71568537f9b7b2778d9cc47/content/video"
        logger.info("Content location : %s", content_location)
        content_location_new = content_location.replace("https://as-storage.asm.skype.com/", "https://prod.asyncgw.teams.microsoft.com/")
        logger.info("Content location new: %s", content_location_new)

        recording_data = call_automation_client.download_recording(content_location_new)
        with open("Recording_File.wav", "wb") as binary_file:
            binary_file.write(recording_data.read())
        return RedirectResponse(url="/")
    except Exception as ex:
        logger.error("Failed to download recording --> %s", str(ex))

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
        # metadata_location = "https://as-storage.asm.skype.com/v1/objects/0-jhb-d4-98459381f71568537f9b7b2778d9cc47/content/acsmetadata"
        logger.info("Metadata location: %s", metadata_location)
        metadata_location_new = metadata_location.replace("https://as-storage.asm.skype.com/", "https://prod.asyncgw.teams.microsoft.com/")
        logger.info("Metadata location new: %s", metadata_location_new)
        recording_data = call_automation_client.download_recording(metadata_location_new)
        with open("Recording_metadata.json", "wb") as binary_file:
            binary_file.write(recording_data.read())
        return RedirectResponse(url="/")
    except Exception as ex:
        logger.error("Failed to download metadata --> %s", str(ex))
 
# 1. API
@app.post(
    "/outboundCall",
    tags=["Call Management"],
    summary="Initiate an outbound PSTN call",
    description="Initiates an outbound call to a phone number.",
    responses={
        302: {"description": "Redirect to home page after initiating call"}
    }
)
# 2. Handler
async def outbound_call_handler():
    """Initiate an outbound PSTN call."""
    call_connection_properties = await create_pstn_call()
    print(f"Outbound PSTN call initiated with connection id: {call_connection_properties.call_connection_id}")
    print(f"Outbound PSTN call initiated with correlation id: {call_connection_properties.correlation_id}")

    return redirect("/")

# 3. Function
async def create_pstn_call():
    target_participant = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
    source_caller = PhoneNumberIdentifier(ACS_PHONE_NUMBER)

    media_streaming_options = MediaStreamingOptions(
        transport_url= WEBSOCKET_URI_HOST,
        transport_type= StreamingTransportType.WEBSOCKET,
        content_type= MediaStreamingContentType.AUDIO,
        audio_channel_type= MediaStreamingAudioChannelType.UNMIXED,
        audio_format=AudioFormat.PCM16_K_MONO,
        start_media_streaming= True
    )

    transcription_options = TranscriptionOptions(
        # transport_url= "https://abc.com",
        transport_url= WEBSOCKET_URI_HOST,
        transport_type= StreamingTransportType.WEBSOCKET,
        locale="en-us",
        start_transcription=True
    )

    call_connection_properties = await call_automation_client.create_call(
        target_participant=[target_participant],
        callback_url=CALLBACK_EVENTS_URI,
        cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT,
        source_caller_id_number=source_caller,
        # media_streaming= media_streaming_options,
        # transcription=transcription_options
    )
    print(f"Created call with connection id: {call_connection_properties.call_connection_id}")
    return call_connection_properties

from starlette.responses import RedirectResponse as redirect



@app.post(
    "/acsoutboundCall",
    tags=["Outbound Call API's"],
    summary="Initiate an outbound call",
    description="Initiates an outbound call to a phone number or ACS user.",
    responses={
        302: {"description": "Redirect to home page after initiating call"}
    }
)
async def outbound_acs_call_handler():
    """Initiate an outbound call."""
    await create_call_acs()
    return RedirectResponse(url="/")

@app.post(
    "/tpeoutboundCall",
    tags=["Outbound Call API's"],
    summary="Initiate an outbound call",
    description="Initiates an outbound call to a phone number or ACS user.",
    responses={
        302: {"description": "Redirect to home page after initiating call"}
    }
)
async def outbound_tpe_call_handler(
    userId: str = Query(..., description="Target user for the call"),
    tenantId: str = Query(..., description="Tenant ID of the target user"),
    resourceId: str = Query(..., description="Resource ID of the target user"),
    teamsAppId: str = Query(..., description="Teams App ID for the call")        
):
    """Initiate an outbound call."""
    await create_call_TPE(userId=userId, tenantId=tenantId, resourceId=resourceId, teamsAppId=teamsAppId)
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
async def group_call_handler(userId: str = Query(..., description="User Id"), enable_loopback_audio: bool = Query(..., description="Enable loopback audio")):
    """Initiate a group call."""
    await create_group_call(userId=userId, enable_loopback_audio=enable_loopback_audio)
    return {"message": "Call initiated"}
    # return RedirectResponse(url="/")

@app.post(
    "/connectCall",
    tags=["Call Management"],
    summary="Connect to an existing call",
    description="Connects to an existing group call by group call ID.",
    responses={
        302: {"description": "Redirect to home page after connecting to call"}
    }
)
async def connect_call_handler(roomId: str = Query(..., description="Room ID to connect to")):
    """Connect to an existing call."""
    await connect_call(roomId=roomId)
    return RedirectResponse(url="/")

@app.post(
    "/playMedia",
    tags=["Media Operations"],
    summary="Play media to call participants",
    description="Plays audio media (e.g., prompts or files) to all or specific call participants.",
    responses={
        302: {"description": "Redirect to home page after playing media"}
    }
)
async def play_media_handler():
    """Play media to call participants."""
    await play_media()
    return RedirectResponse(url="/")

@app.post(
    "/recognizeMediaChoice",
    tags=["Media Operations"],
    summary="Start media recognition",
    description="Starts media recognition (e.g., DTMF or speech) for a call participant.",
    responses={
        302: {"description": "Redirect to home page after starting recognition"}
    }
)
async def play_recognize_choice_handler():
    """Start media recognition."""
    await play_recognize_choice()
    return RedirectResponse(url="/docs")

@app.post(
    "/recognizeMediaSpeech",
    tags=["Media Operations"],
    summary="Start media recognition",
    description="Starts media recognition (e.g., DTMF or speech) for a call participant.",
    responses={
        302: {"description": "Redirect to home page after starting recognition"}
    }
)
async def play_recognize_Speech_handler():
    """Start media recognition."""
    await play_recognize_speech()
    return RedirectResponse(url="/docs")

@app.post(
    "/recognizeMediaSpeechOrDtmf",
    tags=["Media Operations"],
    summary="Start media recognition",
    description="Starts media recognition (e.g., DTMF or speech) for a call participant.",
    responses={
        302: {"description": "Redirect to home page after starting recognition"}
    }
)
async def play_recognize_SpeechOrDtmf_handler():
    """Start media recognition."""
    await play_recognize_speech_or_dtmf()
    return RedirectResponse(url="/docs")

@app.post(
    "/recognizeMediaDtmf",
    tags=["Media Operations"],
    summary="Start media recognition",
    description="Starts media recognition (e.g., DTMF or speech) for a call participant.",
    responses={
        302: {"description": "Redirect to home page after starting recognition"}
    }
)
async def play_recognize_Dtmf_handler():
    """Start media recognition."""
    await play_recognize_dtmf()
    return RedirectResponse(url="/docs")

@app.post(
    "/startContinuousDtmf",
    tags=["DTMF API's"],
    summary="Start continuous DTMF recognition",
    description="Starts continuous DTMF tone recognition for a call participant.",
    responses={302: {"description": "Redirect to home page after starting DTMF recognition"}}
)
async def start_continuous_dtmf_tones_handler(
):
    target = get_communication_target()
    await call_automation_client.get_call_connection(call_connection_id).start_continuous_dtmf_recognition(target_participant=target)
    logger.info("Continuous Dtmf recognition started. press 1 on dialpad.")
    return RedirectResponse(url="/")

@app.post(
    "/stopContinuousDtmf",
    tags=["DTMF API's"],
    summary="Stop continuous DTMF recognition for PSTN",
    description="Stops continuous DTMF tone recognition for a PSTN participant in an active call.",
    responses={302: {"description": "Redirect to home page after stopping DTMF recognition"}}
)
async def stop_continuous_dtmf_tones_handler(
):
    target = get_communication_target()
    await call_automation_client.get_call_connection(call_connection_id).stop_continuous_dtmf_recognition(target_participant=target)
    logger.info("Continuous Dtmf recognition stopped.")
    return RedirectResponse(url="/")

@app.post(
    "/sendDTMFTones",
    tags=["DTMF API's"],
    summary="Send DTMF tones to PSTN user",
    description="Sends DTMF tones to a PSTN participant in a call.",
    responses={
        302: {"description": "Redirect to home page after sending DTMF tones"}
    }
)
async def send_dtmf_tones_handler(
):
    target = get_communication_target()
    tones = [DtmfTone.ONE,DtmfTone.TWO]
    await call_automation_client.get_call_connection(call_connection_id).send_dtmf_tones(tones=tones,target_participant=target)
    logger.info("Send dtmf tone started.")
    return RedirectResponse(url="/")

@app.post(
    "/addParticipantpstn",
    tags=["Add/Remove Participant API's"],
    summary="Add participant to call",
    description="Adds a new participant PSTN to an active call.",
    responses={
        302: {"description": "Redirect to home page after adding participant"}
    }
)
async def add_participant_handler(
    targetParticipant: str = Query(..., description="Phone number of the target participant (e.g., +1234567890)")
):
    """Add participant to call."""
    await add_participant_pstn(targetParticipant)
    return RedirectResponse(url="/")


async def add_participant_pstn(targetParticipant: str):
    """Add a PSTN phone number as a participant."""
    add_participant_result = await call_automation_client.get_call_connection(call_connection_id).add_participant(
        target_participant=PhoneNumberIdentifier(targetParticipant),  # <-- FIXED LINE
        operation_context="addPstnUserContext",
        invitation_timeout=60,
        # source_caller_id_number=PhoneNumberIdentifier(ACS_PHONE_NUMBER)  # <-- FIXED LINE
    )
    invitation_id = add_participant_result.invitation_id
    logger.info(f"INVITATION ID:-->  {invitation_id}")

@app.post(
    "/addParticipantTeams",
    tags=["Add/Remove Participant API's"],
    summary="Add participant to call",
    description="Adds a new participant Teams to an active call.",
    responses={
        302: {"description": "Redirect to home page after adding participant"}
    }
)
async def add_teams_participant_handler(
    targetParticipant: str = Query(..., description="Teamstarget participant")
):
    """Add participant to call."""
    await add_teams_participant_pstn(targetParticipant)
    return RedirectResponse(url="/")


async def add_teams_participant_pstn(targetParticipant: str):
    """Add a Teams phone number as a participant."""

    teams_phone_caller_details = TeamsPhoneCallerDetails(
        name="ACS Bot",
        phone_number="+14255550123",
        caller=MicrosoftTeamsUserIdentifier(targetParticipant),
        is_authenticated=True,
        record_id="12345",
        screen_pop_url="https://example.com/screenpop"
    )
    add_participant_result = await call_automation_client.get_call_connection(call_connection_id).add_participant(
        target_participant=MicrosoftTeamsUserIdentifier(targetParticipant),  # <-- FIXED LINE
        operation_context="addTeamsUserContext",
        invitation_timeout=60,
        teams_phone_call_details=TeamsPhoneCallDetails(
            session_id="12321",
            call_topic="Test Call",
            teams_phone_caller=teams_phone_caller_details
        )
    )
    invitation_id = add_participant_result.invitation_id
    logger.info(f"INVITATION ID:-->  {invitation_id}")

@app.post(
    "/addParticipantTPEUser",
    tags=["Add/Remove Participant API's"],
    summary="Add participant to call",
    description="Adds a new participant TPEUser to an active call.",
    responses={
        302: {"description": "Redirect to home page after adding participant"}
    }
)
async def add_TPEUser_participant_handler(
    userId: str = Query(..., description="User Id"),
    tenantId: str = Query(..., description="Tenant Id"),
    resourceId: str = Query(..., description="Resource Id"),
):
    """Add participant to call."""
    await add_TPEUser_participant(userId, tenantId, resourceId)
    return RedirectResponse(url="/")


async def add_TPEUser_participant(userId: str, tenantId: str, resourceId: str):
    """Add a TPEUser as a participant."""
    add_participant_result = await call_automation_client.get_call_connection(call_connection_id).add_participant(
        target_participant=TeamsExtensionUserIdentifier(user_id=userId, tenant_id=tenantId, resource_id=resourceId),  # <-- FIXED LINE
        operation_context="addTPEUserContext",
        invitation_timeout=60
    )
    invitation_id = add_participant_result.invitation_id
    logger.info(f"INVITATION ID:-->  {invitation_id}")

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
    target_participant: str = Query(..., description="Target ACS participant identifier (e.g., user ID)"),
):
    logger.info(f"Adding ACS participant {target_participant} to call {call_connection_id}")

    connection = call_automation_client.get_call_connection(call_connection_id=call_connection_id)
    await connection.add_participant(
        target_participant=CommunicationUserIdentifier(target_participant),
        operation_context="addAcsUserContext",
        invitation_timeout=30
    )

    logger.info("ACS participant added successfully")
    return RedirectResponse(url="/")


@app.post(
    "/api/participants/cancelAddParticipantAsync",
    tags=["Add/Remove Participant API's"],
    summary="Cancel adding a participant to an active call",
    description="Cancels the operation of adding a participant (ACS or PSTN) to an ongoing call.",
    responses={
        302: {"description": "Redirect to home page after cancelling participant addition"}
    }
)
async def cancel_add_participant_handler(
    invitation_id: str = Query(..., description="Invitation ID"),
):
    await cancel_add_participant(invitation_id=invitation_id)
    return RedirectResponse(url="/")


async def cancel_add_participant(invitation_id: str):
    

    await call_automation_client.get_call_connection(call_connection_id).cancel_add_participant_operation(invitation_id=invitation_id,operation_context="CancleAddParticipantContext")
    
    logger.info("Participant addition cancelled successfully")


@app.post(
    "/api/participants/removeParticipantAsync",
    tags=["Add/Remove Participant API's"],
    summary="Remove a participant from an active call",
    description="Removes a participants from an ongoing call.",
    responses={
        302: {"description": "Redirect to home page after removing participant"}
    }
)
async def remove_participant_handler():
    target = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
    await call_automation_client.get_call_connection(call_connection_id).remove_participant(
        target_participant=target,
        operation_context="removeParticipantContext"
    )
    return RedirectResponse(url="/")

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
    description="Mutes a participant in an ongoing call.",
    responses={
        302: {"description": "Redirect to home page after muting participant"}
    }
)
async def mute_participant_handler(
    target_participant: str = Query(..., description="Participant identifier")
):
    target = MicrosoftTeamsUserIdentifier(target_participant)
    await call_automation_client.get_call_connection(call_connection_id).mute_participant(
        target_participant=target,
        operation_context="muteParticipantContext"
    )
    return Response({
        "message": "Participant muted successfully"
    })

@app.post(
    "/api/participants/muteTPEParticipantAsync",
    tags=["Add/Remove Participant API's"],
    summary="Mute a participant in an active call",
    description="Mutes a participant in an ongoing call.",
    responses={
        302: {"description": "Redirect to home page after muting participant"}
    }
)
async def mute_tpe_participant_handler(
    userId: str = Query(..., description="Participant identifier"),
    tenantId: str = Query(..., description="Tenant ID of the participant"),
    resourceId: str = Query(..., description="Resource ID of the participant")
):
    target = TeamsExtensionUserIdentifier(user_id=userId, tenant_id=tenantId, resource_id=resourceId)
    await call_automation_client.get_call_connection(call_connection_id).mute_participant(
        target_participant=target,
        operation_context="muteParticipantContext"
    )
    return RedirectResponse(url="/")


# async def hold_participant(call_connection_id: str, participant_id: str, is_acs_user: bool, hold_prompt_url: str = None):
#     logger.info(f"Putting participant {participant_id} on hold in call {call_connection_id}, isAcsUser={is_acs_user}")

#     # target = (
#     #     CommunicationUserIdentifier(participant_id)
#     #     if is_acs_user else
#     #     PhoneNumberIdentifier(participant_id)
#     # )
#     target = get_communication_target()

#     connection = call_automation_client.get_call_connection(call_connection_id)

#     await connection.hold(
#         target_participant=target,
#         play_source=
#         operation_context="holdParticipantContext"
#     )

#     logger.info("Participant is now on hold.")

# 🚀 Route Handler
@app.post(
    "/api/participants/holdParticipantAsync",
    tags=["Hold/Unhold Participant API's"],
    summary="Put participant on hold",
    description="Puts a participant (ACS or PSTN) on hold with an optional hold prompt.",
    responses={
        302: {"description": "Redirect to home page after putting participant on hold"}
    }
)
async def hold_participant_handler(

):
    await hold_participant()
    return RedirectResponse(url="/")

@app.post(
    "/api/participants/holdTPEParticipantAsync",
    tags=["Hold/Unhold Participant API's"],
    summary="Put participant on hold",
    description="Puts a participant (ACS or PSTN) on hold with an optional hold prompt.",
    responses={
        302: {"description": "Redirect to home page after putting participant on hold"}
    }
)
async def hold_tpe_participant_handler(
    userId: str = Query(..., description="User Id of the participant"),
    tenantId: str = Query(..., description="Tenant Id of the participant"),
    resourceId: str = Query(..., description="Resource Id of the participant"),

):
    await hold_tpe_participant(userId=userId, tenantId=tenantId, resourceId=resourceId)
    return RedirectResponse(url="/")
# async def unhold_participant(call_connection_id: str, participant_id: str, is_acs_user: bool):
#     logger.info(f"Unholding participant {participant_id} in call {call_connection_id}, isAcsUser={is_acs_user}")

#     target = (
#         CommunicationUserIdentifier(participant_id)
#         if is_acs_user else
#         PhoneNumberIdentifier(participant_id)
#     )

#     connection = call_automation_client.get_call_connection(call_connection_id)

#     await connection.resume_participant(
#         target_participant=target,
#         operation_context="unholdParticipantContext"
#     )

#     logger.info("Participant is now off hold.")

# 🚀 Route Handler
@app.post(
    "/api/participants/unholdParticipantAsync",
    tags=["Hold/Unhold Participant API's"],
    summary="Take participant off hold",
    description="Takes a participant (ACS or PSTN) off hold in an active call.",
    responses={
        302: {"description": "Redirect to home page after taking participant off hold"}
    }
)
async def unhold_participant_handler(
):
    await unhold_participant()
    return RedirectResponse(url="/")

@app.post(
    "/api/participants/unholdTPEParticipantAsync",
    tags=["Hold/Unhold Participant API's"],
    summary="Take participant off hold",
    description="Takes a participant (ACS or PSTN) off hold in an active call.",
    responses={
        302: {"description": "Redirect to home page after taking participant off hold"}
    }
)
async def unhold_tpe_participant_handler(
    userId: str = Query(..., description="User Id of the participant"),
    tenantId: str = Query(..., description="Tenant Id of the participant"),
    resourceId: str = Query(..., description="Resource Id of the participant")
):
    # await unhold_tpe_participant(userId=userId, tenantId=tenantId, resourceId=resourceId)
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
async def get_pstn_participant_handler(
    target_participant: str = Query(..., description="Target participant identifier (e.g., user ID or phone number)")
):
    """Get participant details."""
    target = PhoneNumberIdentifier(target_participant)
    await get_participant(target)
    return RedirectResponse(url="/")

@app.post(
    "/getACSParticipant",
    tags=["Hold Participant API's"],
    summary="Get participant details",
    description="Retrieves details of a specific participant in an active call.",
    responses={
        302: {"description": "Redirect to home page after retrieving participant details"}
    }
)
async def get_acs_participant_handler(
    target_participant: str = Query(..., description="Target participant identifier (e.g., user ID or phone number)")
):
    """Get participant details."""
    target = CommunicationUserIdentifier(target_participant)
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
   # print(f"List of Participant initiated with connection id: {call_connection_properties.correlation_id}")
    return RedirectResponse(url="/")


    

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
                "recording_state_callback_url": CALLBACK_EVENTS_URI,
                "recording_storage": recording_storage,
                "pause_on_start": is_pause_on_start
            }
            if is_recording_with_call_connection_id
            else {
                "call_locator": call_locator,
                "recording_content_type": RecordingContent.AUDIO_VIDEO,
                "recording_channel_type": RecordingChannel.MIXED,
                "recording_format_type": RecordingFormat.MP4,
                "recording_state_callback_url": CALLBACK_EVENTS_URI,
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
                "recording_state_callback_url": CALLBACK_EVENTS_URI,
                "recording_storage": recording_storage,
                "pause_on_start": is_pause_on_start
            }
            if is_recording_with_call_connection_id
            else {
                "call_locator": call_locator,
                "recording_content_type": RecordingContent.AUDIO,
                "recording_channel_type": RecordingChannel.UNMIXED,
                "recording_format_type": RecordingFormat.WAV,
                "recording_state_callback_url": CALLBACK_EVENTS_URI,
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
                "recording_state_callback_url": CALLBACK_EVENTS_URI,
                "recording_storage": recording_storage,
                "pause_on_start": is_pause_on_start
            }
            if is_recording_with_call_connection_id
            else {
                "call_locator": call_locator,
                "recording_content_type": RecordingContent.AUDIO,
                "recording_channel_type": RecordingChannel.MIXED,
                "recording_format_type": RecordingFormat.WAV,
                "recording_state_callback_url": CALLBACK_EVENTS_URI,
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
                "recording_state_callback_url": CALLBACK_EVENTS_URI,
                "recording_storage": recording_storage,
                "pause_on_start": is_pause_on_start
            }
            if is_recording_with_call_connection_id
            else {
                "call_locator": call_locator,
                "recording_content_type": RecordingContent.AUDIO,
                "recording_channel_type": RecordingChannel.MIXED,
                "recording_format_type": RecordingFormat.MP3,
                "recording_state_callback_url": CALLBACK_EVENTS_URI,
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
    "/transferCallPSTNToPSNTAsync",
    tags=["Transfer Call APIs"],
    summary="Transfer call from one ACS participant to another",
    description="Transfers the call from a current ACS user (transferee) to another ACS user (target).",
    responses={302: {"description": "Redirects to homepage after transfer"}}
)
async def transfer_call_pstn_to_pstn_participant_handler(
    transferee: str = Query(..., description="Transferee ACS user identifier"),
    target: str = Query(..., description="Target user identifier")
):
    """Transfer call to a participant."""
    transfer_target = PhoneNumberIdentifier(target)
    transferee_taget = PhoneNumberIdentifier(transferee)
    logger.info("Transfer target:- %s", transfer_target.raw_id)
    await call_automation_client.get_call_connection(call_connection_id).transfer_call_to_participant(
         target_participant=transfer_target,
         operation_context="transferCallContext",
         transferee=transferee_taget,
         )
    logger.info("Transfer call initiated.")
    return RedirectResponse(url="/")

@app.post(
    "/transferCallPSTNToACSAsync",
    tags=["Transfer Call APIs"],
    summary="Transfer call from one ACS participant to another",
    description="Transfers the call from a current ACS user (transferee) to another ACS user (target).",
    responses={302: {"description": "Redirects to homepage after transfer"}}
)
async def transfer_call_pstn_to_acs_participant_handler(
    transferee: str = Query(..., description="Transferee ACS user identifier"),
    target: str = Query(..., description="Target user identifier")
):
    """Transfer call to a participant."""
    transfer_target = CommunicationUserIdentifier(target)
    transferee_target = PhoneNumberIdentifier(transferee)
    logger.info("Transfer target:- %s", transfer_target.raw_id)
    await call_automation_client.get_call_connection(call_connection_id).transfer_call_to_participant(
         target_participant=transfer_target,
         operation_context="transferCallContext",
         transferee=transferee_target,
         )
    logger.info("Transfer call initiated.")
    return RedirectResponse(url="/")

@app.post(
    "/transferCallPSTNToTeamsAsync",
    tags=["Transfer Call APIs"],
    summary="Transfer call from one ACS participant to another",
    description="Transfers the call from a current ACS user (transferee) to another ACS user (target).",
    responses={302: {"description": "Redirects to homepage after transfer"}}
)
async def transfer_call_pstn_to_teams_participant_handler(
    transferee: str = Query(..., description="Transferee ACS user identifier"),
    target: str = Query(..., description="Target user identifier")
):
    """Transfer call to a participant."""
    transfer_target = MicrosoftTeamsUserIdentifier(target)
    transferee_taget = PhoneNumberIdentifier(transferee)
    logger.info("Transfer target:- %s", transfer_target.raw_id)
    await call_automation_client.get_call_connection(call_connection_id).transfer_call_to_participant(
         target_participant=transfer_target,
         operation_context="transferCallContext",
         transferee=transferee_taget,
         )
    logger.info("Transfer call initiated.")
    return RedirectResponse(url="/")

@app.post(
    "/transferCallTeamsToPSTNAsync",
    tags=["Transfer Call APIs"],
    summary="Transfer call from one ACS participant to another",
    description="Transfers the call from a current ACS user (transferee) to another ACS user (target).",
    responses={302: {"description": "Redirects to homepage after transfer"}}
)
async def transfer_call_teams_to_pstn_participant_handler(
    transferee: str = Query(..., description="Transferee ACS user identifier"),
    target: str = Query(..., description="Target user identifier")
):
    """Transfer call to a participant."""
    transferee_taget = MicrosoftTeamsUserIdentifier(transferee)
    transfer_target = PhoneNumberIdentifier(target)
    logger.info("Transfer target:- %s", transfer_target.raw_id)
    await call_automation_client.get_call_connection(call_connection_id).transfer_call_to_participant(
         target_participant=transfer_target,
         operation_context="transferCallContext",
         transferee=transferee_taget,
         )
    logger.info("Transfer call initiated.")
    return RedirectResponse(url="/")

@app.post(
    "/transferCallPSTNToTPEAsync",
    tags=["Transfer Call APIs"],
    summary="Transfer call from one ACS participant to another",
    description="Transfers the call from a current ACS user (transferee) to another ACS user (target).",
    responses={302: {"description": "Redirects to homepage after transfer"}}
)
async def transfer_call_pstn_to_tpe_participant_handler(
    userId: str = Query(..., description="Transferee ACS user identifier"),
    tenantId: str = Query(..., description="Transferee ACS user identifier"),
    resourceId: str = Query(..., description="Transferee ACS user identifier"),
    transferee: str = Query(..., description="Target user identifier")
):
    """Transfer call to a participant."""
    transfer_target = TeamsExtensionUserIdentifier(user_id=userId, tenant_id=tenantId, resource_id=resourceId)
    transferee_taget = PhoneNumberIdentifier(transferee)
    logger.info("Transfer target:- %s", transfer_target.raw_id)
    await call_automation_client.get_call_connection(call_connection_id).transfer_call_to_participant(
         target_participant=transfer_target,
         operation_context="transferCallContext",
         transferee=transferee_taget,
         )
    logger.info("Transfer call initiated.")
    return RedirectResponse(url="/")

@app.post(
    "/transferCallTPEToPSTNAsync",
    tags=["Transfer Call APIs"],
    summary="Transfer call from one ACS participant to another",
    description="Transfers the call from a current ACS user (transferee) to another ACS user (target).",
    responses={302: {"description": "Redirects to homepage after transfer"}}
)
async def transfer_call_tpe_to_pstn_participant_handler(
    userId: str = Query(..., description="Transferee ACS user identifier"),
    tenantId: str = Query(..., description="Transferee ACS user identifier"),
    resourceId: str = Query(..., description="Transferee ACS user identifier"),
    target: str = Query(..., description="Target user identifier")
):
    """Transfer call to a participant."""
    transferee_taget = TeamsExtensionUserIdentifier(user_id=userId, tenant_id=tenantId, resource_id=resourceId)
    transfer_target = PhoneNumberIdentifier(target)
    logger.info("Transfer target:- %s", transfer_target.raw_id)
    await call_automation_client.get_call_connection(call_connection_id).transfer_call_to_participant(
         target_participant=transfer_target,
         operation_context="transferCallContext",
         transferee=transferee_taget,
         )
    logger.info("Transfer call initiated.")
    return RedirectResponse(url="/")

# async def start_recording_logic(
#     call_connection_id: str,
#     is_recording_with_call_connection_id: bool,
#     is_pause_on_start: bool
# ):
#     global recording_id
#     try:
#         call_connection_properties = await call_automation_client.get_call_connection(
#             call_connection_id
#         ).get_call_properties()
#         server_call_id = call_connection_properties.server_call_id
#         correlation_id = call_connection_properties.correlation_id
#         call_locator = ServerCallLocator(server_call_id)

#         print(f"console.log: 🎙️ Starting audio recording on call ID: {call_connection_id}")
#         print(f"console.log: 🔗 Correlation ID: {correlation_id}")

#         recording_storage = (
#             AzureBlobContainerRecordingStorage(BRING_YOUR_OWN_STORAGE_URL)
#             if IS_BYOS
#             else AzureCommunicationsRecordingStorage()
#         )

#         recording_options = (
#             {
#                 "call_connection_id": call_connection_properties.call_connection_id,
#                 "recording_content_type": RecordingContent.AUDIO,
#                 "recording_channel_type": RecordingChannel.UNMIXED,
#                 "recording_format_type": RecordingFormat.WAV,
#                 "recording_state_callback_url": CALLBACK_EVENTS_URI,
#                 "recording_storage": recording_storage,
#                 "pause_on_start": is_pause_on_start
#             }
#             if is_recording_with_call_connection_id
#             else {
#                 "call_locator": call_locator,
#                 "recording_content_type": RecordingContent.AUDIO,
#                 "recording_channel_type": RecordingChannel.UNMIXED,
#                 "recording_format_type": RecordingFormat.WAV,
#                 "recording_state_callback_url": CALLBACK_EVENTS_URI,
#                 "recording_storage": recording_storage,
#                 "pause_on_start": is_pause_on_start
#             }
#         )

#         recording_result = await call_automation_client.start_recording(**recording_options)
#         recording_id = recording_result.recording_id

#         print(
#             f"console.log: ✅ Recording started. RecordingId: {recording_id}, "
#             f"CallConnectionId: {call_connection_id}, CorrelationId: {correlation_id}, "
#             f"Status: {recording_result.recording_state}"
#         )

#         return CloudEvent(
#             call_connection_id=call_connection_id,
#             correlation_id=correlation_id,
#             status=f"Recording started. RecordingId: {recording_id}. Status: {recording_result.recording_state}"
#         )

#     except Exception as ex:
#         error_message = f"Error starting recording: {str(ex)}. CallConnectionId: {call_connection_id}"
#         print(f"console.log: ❌ {error_message}")
#         raise HTTPException(
#             status_code=500,
#             detail=error_message
#         )


async def start_recording():
     global recording_storage
     if IS_BYOS:
         recording_storage=AzureBlobContainerRecordingStorage("BRING_YOUR_STORAGE_URL")
     else:
         recording_storage=AzureCommunicationsRecordingStorage()
         
     properties = get_call_properties()
     server_call_id = properties.server_call_id
     
     recording_result = call_automation_client.start_recording(
                    call_connection_id=properties.call_connection_id,
                    # server_call_id=server_call_id,
                    # room_id="9948475894108163",
                    recording_content_type = RecordingContent.AUDIO,
                    recording_channel_type = RecordingChannel.MIXED,
                    recording_format_type = RecordingFormat.WAV,
                    recording_storage= AzureCommunicationsRecordingStorage(),
                    pause_on_start = False,
                    recording_state_callback_url=CALLBACK_EVENTS_URI
                    )
     global recording_id
     recording_id=recording_result.recording_id
     logger.info("Recording started...")
     logger.info("Recording Id --> %s", recording_id)

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
):
    await start_recording()
    return RedirectResponse(url="/")

# async def pause_recording_logic(recording_id: str):
#     try:
#         if not recording_id:
#             print(f"console.log: ⚠️ Recording id is empty.")
#             raise HTTPException(
#                 status_code=400,
#                 detail="Recording id is empty."
#             )

#         recording_state = await get_recording_state(recording_id)  # Update get_recording_state to accept recording_id
#         if recording_state == "active":
#             print(f"console.log: ⏸️ Pausing recording with RecordingId: {recording_id}")
#             await call_automation_client.pause_recording(recording_id)
#             print(f"console.log: ✅ Recording is paused.")
#             return CloudEvent(
#                 recording_id=recording_id,
#                 status="Recording is paused."
#             )
#         else:
#             print(f"console.log: ℹ️ Recording is already inactive. RecordingId: {recording_id}")
#             return CloudEvent(
#                 recording_id=recording_id,
#                 status="Recording is already inactive."
#             )

#     except Exception as ex:
#         error_message = f"Error pausing recording: {str(ex)}. RecordingId: {recording_id}"
#         print(f"console.log: ❌ {error_message}")
#         raise HTTPException(
#             status_code=500,
#             detail=error_message
#         )


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
):
    await pause_recording()
    return RedirectResponse(url="/")


# async def resume_recording_logic(recording_id: str, call_connection_id: str):
#     try:
#         if not recording_id:
#             print(f"console.log: ⚠️ Recording id is empty.")
#             raise HTTPException(
#                 status_code=400,
#                 detail="Recording id is empty."
#             )

#         if not call_connection_id:
#             print(f"console.log: ⚠️ Call connection id is empty.")
#             raise HTTPException(
#                 status_code=400,
#                 detail="Call connection id is empty."
#             )

#         # Fetch call properties to get correlationId
#         call_connection_properties = await call_automation_client.get_call_connection(
#             call_connection_id
#         ).get_call_properties()
#         correlation_id = call_connection_properties.correlation_id

#         recording_state = await get_recording_state(recording_id)  # Update get_recording_state to accept recording_id
#         if recording_state == "inactive":
#             print(f"console.log: ▶️ Resuming recording with RecordingId: {recording_id}")
#             await call_automation_client.resume_recording(recording_id)
#             print(f"console.log: ✅ Recording is resumed.")
#             status_message = "Recording is resumed."
#         else:
#             print(f"console.log: ℹ️ Recording is already active. RecordingId: {recording_id}")
#             status_message = "Recording is already active."

#         return CloudEventData(
#             callConnectionId=call_connection_id,
#             correlationId=correlation_id,
#             resultInformation={"status": status_message}
#         )

#     except Exception as ex:
#         error_message = f"Error resuming recording: {str(ex)}. RecordingId: {recording_id}, CallConnectionId: {call_connection_id}"
#         print(f"console.log: ❌ {error_message}")
#         raise HTTPException(
#             status_code=500,
#             detail=error_message
#         )

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
):
    await resume_recording()
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
async def play_with_interrupt_media_flag_handler(interrupt1: bool, interrupt2: bool):
    """Play media with interrupt flag."""
    await play_with_interrupt_media_flag(interrupt1, interrupt2)
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
async def hangup_call_handler(isForEveryOne: bool = Query(..., description="If true, hang up for everyone in the call")):
    """Hang up call."""
    await hangup_call(isForEveryOne)
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
async def stop_media_streaming():
    """Stops media streaming for a given call connection."""
    try:
        await call_automation_client.get_call_connection(call_connection_id).stop_media_streaming()
        
        return {"message": "Media streaming stopped successfully."}
    except Exception as e:
        log.error(f"Error stopping media streaming: {e}")
        raise HTTPException(status_code=500, detail="Failed to stop media streaming.")
    
@app.post(
    "/stopMediaStreamingWithOptions",
    tags=["Media Streaming"],
    summary="Stop media streaming",
    description="Stops media streaming for a given call connection.",
    responses={
        200: {"description": "Successfully stopped media streaming"},
        400: {"description": "Bad Request, call connection ID is missing"},
        500: {"description": "Internal server error while stopping media streaming"},
    },
)
async def stop_media_streaming_with_options():
    """Stops media streaming for a given call connection."""
    try:
        await call_automation_client.get_call_connection(call_connection_id).stop_media_streaming(
            operation_context="stopMediaStreamingContext"
        )
        
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
async def start_media_streaming():
    """Starts media streaming for a given call connection."""
    try:
        await call_automation_client.get_call_connection(call_connection_id).start_media_streaming()
        logger.info(f"Started media streaming for call: {call_connection_id}")
        return {"message": "Media streaming started successfully."}
    except Exception as e:
        logger.error(f"Error starting media streaming: {e}")
        raise HTTPException(status_code=500, detail="Failed to start media streaming.")
    
@app.post(
    "/startMediaStreamingWithOptions",
    tags=["Media Streaming"],
    summary="Start media streaming",
    description="Starts media streaming for a given call connection.",
    responses={
        200: {"description": "Successfully started media streaming"},
        400: {"description": "Bad Request, call connection ID is missing"},
        500: {"description": "Internal server error while starting media streaming"},
    },
)
async def start_media_streaming_with_options():
    """Starts media streaming for a given call connection."""
    try:
        await call_automation_client.get_call_connection(call_connection_id).start_media_streaming(
            operation_context="StartMediaStreamingContext"
        )
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
    "/startTranscriptionAsync",
    tags=["Transcription"],
    summary="Start call transcription asynchronously",
    description="Starts the transcription asynchronously for a given call connection.",
    responses={
        200: {"description": "Successfully start transcription"},
        400: {"description": "Bad Request, call connection ID is missing"},
        500: {"description": "Internal server error while starting transcription"},
    },
)
async def start_transcription_async():
    """Starts transcription asynchronously for a given call connection."""
    try:
        await call_automation_client.get_call_connection(call_connection_id=call_connection_id).start_transcription()
        return {"message": "Transcription start successfully."}
    except Exception as e:
        log.error(f"Error starting transcription: {e}")
        raise HTTPException(status_code=500, detail="Failed to start transcription.")
    
@app.post(
    "/startTranscriptionWithOptionsAsync",
    tags=["Transcription"],
    summary="Start call transcription asynchronously",
    description="Start the transcription asynchronously for a given call connection.",
    responses={
        200: {"description": "Successfully starts transcription"},
        400: {"description": "Bad Request, call connection ID is missing"},
        500: {"description": "Internal server error while start transcription"},
    },
)
async def start_transcription_async():
    """Starts transcription asynchronously for a given call connection."""
    try:
        await call_automation_client.get_call_connection(call_connection_id=call_connection_id).start_transcription(
            operation_context="StartTranscriptionContext"
        )
        return {"message": "Transcription started successfully."}
    except Exception as e:
        log.error(f"Error starting transcription: {e}")
        raise HTTPException(status_code=500, detail="Failed to start transcription.")

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
async def update_transcription():
    """Updates the transcription locale for a given call connection."""
    try:
        await call_automation_client.get_call_connection(call_connection_id=call_connection_id).update_transcription(
            operation_context="UpdateTranscriptionContext",
            locale="en-au"
        )
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
async def stop_transcription_async():
    """Stops transcription asynchronously for a given call connection."""
    try:
        await call_automation_client.get_call_connection(call_connection_id=call_connection_id).stop_transcription()
        return {"message": "Transcription stopped successfully."}
    except Exception as e:
        log.error(f"Error stopping transcription: {e}")
        raise HTTPException(status_code=500, detail="Failed to stop transcription.")
    
@app.post(
    "/stopTranscriptionWithOptionsAsync",
    tags=["Transcription"],
    summary="Stop call transcription asynchronously",
    description="Stops the transcription asynchronously for a given call connection.",
    responses={
        200: {"description": "Successfully stopped transcription"},
        400: {"description": "Bad Request, call connection ID is missing"},
        500: {"description": "Internal server error while stopping transcription"},
    },
)
async def stop_transcription_async():
    """Stops transcription asynchronously for a given call connection."""
    try:
        await call_automation_client.get_call_connection(call_connection_id=call_connection_id).stop_transcription(
            operation_context="StopTranscriptionContext"
        )
        return {"message": "Transcription stopped successfully."}
    except Exception as e:
        log.error(f"Error stopping transcription: {e}")
        raise HTTPException(status_code=500, detail="Failed to stop transcription.")


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
        callback_uri = f"{CALLBACK_URI_HOST}/api/callbacks"

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
        
        text_source = TextSource(text=PLAY_PROMPT, voice_name="en-US-NancyNeural")
        play_sources = [text_source]
        target = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
        # play_to = [CommunicationUserIdentifier(ACS_PHONE_NUMBER)]
        play_to = [target]

        
        await call_automation_client.get_call_connection(call_connection_id=call_connection_id).play_media(
            play_source=text_source,
            play_to=play_to
        )

        logger.info("Successfully played text source to target asynchronously.")
        return {"message": "Successfully played text source to target asynchronously."}

    except Exception as e:
        logger.error(f"Error playing text source to target asynchronously: {e}")
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

        text_source = TextSource(text="Hi, this is test source played through play source thanks. Goodbye!", voice_name="en-US-NancyNeural")

        # PlayToAllOptions is not defined in the SDK; pass play_source and operation_context directly
        await call_automation_client.get_call_connection(call_connection_id).play_media_to_all(
            play_source=text_source,
            operation_context="playToAllContext",
            loop=False,
            operation_callback_url=CALLBACK_EVENTS_URI,
            interrupt_call_media_operation=False
        )

        log.info("Successfully played text source to all asynchronously.")
        return {"message": "Successfully played text source to all asynchronously."}

    except Exception as e:
        log.error(f"Error playing text source to all asynchronously: {e}")
        raise HTTPException(status_code=500, detail="Failed to play text source to all asynchronously.")


@app.post(
    "/playToTargetwithMultipleSources",
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
        
        text_source = TextSource(text=INTERRUPT_PROMPT, voice_name="en-US-NancyNeural")
        file_source = FileSource(url=MAIN_MENU_PROMPT_URI)
        ssml_text = SsmlSource(ssml_text=SSML_INTERRUPT_TEXT)
        play_sources = [text_source, file_source, ssml_text]
        target = PhoneNumberIdentifier(TARGET_PHONE_NUMBER)
        # play_to = [CommunicationUserIdentifier(ACS_PHONE_NUMBER)]
        play_to = [target]

        await call_automation_client.get_call_connection(call_connection_id=call_connection_id).play_media(
            play_source=play_sources,
            play_to=play_to
        )

        logger.info("Successfully played text source to target asynchronously.")
        return {"message": "Successfully played text source to target asynchronously."}

    except Exception as e:
        logger.error(f"Error playing text source to target asynchronously: {e}")
        await call_automation_client.get_call_connection(call_connection_id=call_connection_id).play_media(
            play_source=text_source,
            play_to=play_to
        )

        logger.info("Successfully played text source to target asynchronously.")
        return {"message": "Successfully played text source to target asynchronously."}

    except Exception as e:
        logger.error(f"Error playing text source to target asynchronously: {e}")
        raise HTTPException(status_code=500, detail="Failed to play text source to target asynchronously.")

@app.post(
    "/playToAllwithMultipleSources",
    tags=["Play Media"],
    summary="Play text sources to all",
    description="Plays multiple text sources to all participants asynchronously in an active call.",
    responses={
        200: {"description": "Successfully played text sources to all"},
        500: {"description": "Internal server error while playing text sources to all"},
    },
)
async def play_text_source_to_all():
    """Plays multiple text sources to all participants asynchronously."""
    try:

        text_source = TextSource(text=INTERRUPT_PROMPT, voice_name="en-US-NancyNeural")
        file_source = FileSource(url=MAIN_MENU_PROMPT_URI)
        ssml_text = SsmlSource(ssml_text=SSML_INTERRUPT_TEXT)
        play_sources = [text_source, file_source, ssml_text]

        # PlayToAllOptions is not defined in the SDK; pass play_source and operation_context directly
        await call_automation_client.get_call_connection(call_connection_id).play_media_to_all(
            play_source=play_sources,
            operation_context="playToAllContext",
            loop=False,
            operation_callback_url=CALLBACK_EVENTS_URI,
            interrupt_call_media_operation=False
        )

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

@app.post(
    "/startContinuousDtmf",
    tags=["Play Media"],
    summary="Start continuous DTMF tones",
    description="Starts sending continuous DTMF tones to all participants in an active call.",
    responses={
        200: {"description": "Successfully started sending continuous DTMF tones"},
        500: {"description": "Internal server error while starting continuous DTMF tones"},
    },
)
async def start_continuous_dtmf():
    """Starts sending continuous DTMF tones to all participants in an active call."""
    try:
        await start_continuous_dtmf()
        logger.info("Successfully started sending continuous DTMF tones.")
        return {"message": "Successfully started sending continuous DTMF tones."}

    except Exception as e:
        logger.error(f"Error starting continuous DTMF tones: {e}")
        raise HTTPException(status_code=500, detail="Failed to start continuous DTMF tones.")

@app.post(
    "/stopContinuousDtmf",
    tags=["Play Media"],
    summary="Stop sending continuous DTMF tones",
    description="Stops sending continuous DTMF tones to all participants in an active call.",
    responses={
        200: {"description": "Successfully stopped sending continuous DTMF tones"},
        500: {"description": "Internal server error while stopping continuous DTMF tones"},
    },
)
async def stop_continuous_dtmf():
    """Stops sending continuous DTMF tones to all participants in an active call."""
    try:
        await stop_continuous_dtmf()
        logger.info("Successfully stopped sending continuous DTMF tones.")
        return {"message": "Successfully stopped sending continuous DTMF tones."}

    except Exception as e:
        logger.error(f"Error stopping continuous DTMF tones: {e}")
        raise HTTPException(status_code=500, detail="Failed to stop continuous DTMF tones.")

@app.post(
    "/api/incomingCall",
    tags=["Call Events"],
    summary="Handle incoming call event",
    description="Handles incoming call events from Azure Communication Services and answers the call with media streaming options.",
    responses={
        200: {"description": "Call handled successfully"},
        500: {"description": "Internal server error while handling incoming call"},
    },
)
async def incoming_call_handler(request: Request):
    logger.info("Received incoming call event.")
    try:
        request_body = await request.json()
        for event_dict in request_body:
            event = EventGridEvent.from_dict(event_dict)
            logger.info("Incoming event data --> %s", event.data)

            if event.event_type == SystemEventNames.EventGridSubscriptionValidationEventName:
                validation_code = event.data.get('validationCode')
                return JSONResponse(content={"validationResponse": validation_code}, status_code=200)

            if event.event_type == "Microsoft.Communication.IncomingCall":
                from_data = event.data.get('from', {})
                caller_id = from_data.get("phoneNumber", {}).get("value") if from_data.get("kind") == "phoneNumber" else from_data.get("rawId")
                logger.info("Caller ID: %s", caller_id)

                incoming_call_context = event.data.get('incomingCallContext')
                callback_uri = CALLBACK_EVENTS_URI

                media_streaming_options = MediaStreamingOptions(
                    transport_url=WEBSOCKET_URI_HOST,
                    transport_type=StreamingTransportType.WEBSOCKET,
                    content_type=MediaStreamingContentType.AUDIO,
                    audio_channel_type=MediaStreamingAudioChannelType.UNMIXED,
                    audio_format=AudioFormat.PCM16_K_MONO,
                    # enable_bidirectional=True,
                    # enable_dtmf_tones=True,
                    start_media_streaming=False
                )

                transcription_options = TranscriptionOptions(
                transport_url= WEBSOCKET_URI_HOST,
                transport_type= StreamingTransportType.WEBSOCKET,
                locale="en-us",
                start_transcription=False
                )

                try:
                        answer_call_result = await call_automation_client.answer_call(
                            incoming_call_context=incoming_call_context,
                            media_streaming=media_streaming_options,
                            transcription=transcription_options,
                            cognitive_services_endpoint=COGNITIVE_SERVICES_ENDPOINT,
                        callback_url=callback_uri,
                        enable_loopback_audio=True,
                        operation_context="answerCallContext"
                        )
                        logger.info(f"Call answered, connection ID: {answer_call_result.call_connection_id}")
                        # IS_ANSWERED = False

                except Exception as e:
                    logger.error(f"Failed to answer call: {e}")
                    return JSONResponse(status_code=500, content={"detail": "Failed to answer call"})
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

        return JSONResponse(status_code=200, content={"message": "Call handled successfully"})

    except Exception as ex:
        logger.error(f"Error handling incoming call: {ex}")
        return JSONResponse(status_code=500, content={"detail": "Internal server error while handling incoming call"})

@app.route('/')
def index_handler():
    return render_template("index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8081)