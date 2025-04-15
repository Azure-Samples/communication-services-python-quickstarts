from quart import Quart, request, Response, websocket
from azure.communication.callautomation import (
    CallAutomationClient, SsmlSource, PlayToAllOptions, TranscriptionOptions, TranscriptionTransportType
)
from azure.core.messaging import CloudEvent
from azure.eventgrid import EventGridEvent, SystemEventNames
import asyncio
import json
import uuid
import re
from collections import defaultdict
from httpx import AsyncClient

# Initialize Quart app
app = Quart(__name__)

# Configuration
ACS_CONNECTION_STRING = "<ACS_CONNECTION_STRING>"
COGNITIVE_SERVICE_ENDPOINT = "<COGNITIVE_SERVICE_ENDPOINT>"
AGENT_PHONE_NUMBER = "<AGENT_PHONE_NUMBER>"
DIRECT_LINE_SECRET = "<DIRECT_LINE_SECRET>"
BASE_URI = "<BASE_URI>".rstrip("/")
BASE_WSS_URI = BASE_URI.split("https://")[1]

# Initialize Call Automation Client
call_automation_client = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)

# HTTP client for Direct Line
http_client = AsyncClient(headers={"Authorization": f"Bearer {DIRECT_LINE_SECRET}"})

# Store call contexts
call_store = defaultdict(dict)

@app.route("/", methods=["GET"])
async def home():
    return "Hello ACS CallAutomation - MCS Sample!"

@app.route("/api/incomingCall", methods=["POST"])
async def incoming_call():
    event_grid_events = await request.json
    for event_grid_event in event_grid_events:
        event = EventGridEvent.from_dict(event_grid_event)
        if event.event_type == SystemEventNames.EventGridSubscriptionValidationEventName:
            validation_code = event.data["validationCode"]
            return Response(response=json.dumps({"validationResponse": validation_code}), status=200)

        incoming_call_context = event.data["incomingCallContext"]
        callback_uri = f"{BASE_URI}/api/calls/{uuid.uuid4()}"

        transcription_options = TranscriptionOptions(
            transport_url=f"wss://{BASE_WSS_URI}/ws",
            locale="en-US",
            start_transcription=True,
            transport_type=TranscriptionTransportType.WEBSOCKET
        )

        try:
            answer_call_result = await call_automation_client.answer_call(
                incoming_call_context=incoming_call_context,
                callback_url=callback_uri,
                cognitive_services_endpoint=COGNITIVE_SERVICE_ENDPOINT,
                transcription=transcription_options
            )
            correlation_id = answer_call_result.call_connection_properties.correlation_id
            if correlation_id:
                call_store[correlation_id] = {"correlation_id": correlation_id}
        except Exception as ex:
            app.logger.error(f"Error answering call: {ex}")
    return Response(status=200)

@app.route("/api/calls/<context_id>", methods=["POST"])
async def call_events(context_id):
    cloud_events = await request.json
    for cloud_event in cloud_events:
        event = CloudEvent.from_dict(cloud_event)
        call_connection = call_automation_client.get_call_connection(event.data["callConnectionId"])
        call_media = call_connection.get_call_media()
        correlation_id = event.data["correlationId"]

        if event.type == "Microsoft.Communication.CallConnected":
            conversation = await start_conversation()
            conversation_id = conversation["conversationId"]
            call_store[correlation_id]["conversation_id"] = conversation_id

            asyncio.create_task(listen_to_bot_websocket(conversation["streamUrl"], call_connection))
            await send_message(conversation_id, "Hi")

        elif event.type == "Microsoft.Communication.PlayFailed":
            app.logger.info("Play Failed")

        elif event.type == "Microsoft.Communication.PlayCompleted":
            app.logger.info("Play Completed")

        elif event.type == "Microsoft.Communication.TranscriptionStarted":
            app.logger.info(f"Transcription started: {event.data['operationContext']}")

        elif event.type == "Microsoft.Communication.TranscriptionStopped":
            app.logger.info(f"Transcription stopped: {event.data['operationContext']}")

        elif event.type == "Microsoft.Communication.CallDisconnected":
            call_store.pop(correlation_id, None)
    return Response(status=200)

@app.websocket('/ws')
async def ws():
    correlation_id = websocket.headers.get("x-ms-call-correlation-id")
    call_connection_id = websocket.headers.get("x-ms-call-connection-id")
    call_media = call_automation_client.get_call_connection(call_connection_id).get_call_media()
    conversation_id = call_store[correlation_id]["conversation_id"]

    try:
        while True:
            message = await websocket.receive()
            if "Intermediate" in message:
                await call_media.cancel_all_media_operations()
            else:
                transcription_data = json.loads(message)
                if transcription_data.get("resultState") == "Final":
                    await send_message(conversation_id, transcription_data["text"])
    except Exception as ex:
        app.logger.error(f"WebSocket error: {ex}")

async def start_conversation():
    response = await http_client.post("https://directline.botframework.com/v3/directline/conversations")
    response.raise_for_status()
    return response.json()

async def listen_to_bot_websocket(stream_url, call_connection):
    async with AsyncClient() as ws_client:
        async with ws_client.stream("GET", stream_url) as websocket:
            async for message in websocket.aiter_text():
                bot_activity = extract_latest_bot_activity(message)
                if bot_activity["type"] == "message":
                    await play_to_all(call_connection.get_call_media(), bot_activity["text"])
                elif bot_activity["type"] == "endOfConversation":
                    await call_connection.hang_up(is_for_everyone=True)

async def send_message(conversation_id, message):
    payload = {
        "type": "message",
        "from": {"id": "user1"},
        "text": message
    }
    await http_client.post(
        f"https://directline.botframework.com/v3/directline/conversations/{conversation_id}/activities",
        json=payload
    )

def extract_latest_bot_activity(raw_message):
    try:
        activities = json.loads(raw_message).get("activities", [])
        for activity in reversed(activities):
            if activity["type"] == "message" and activity["from"]["id"] != "user1":
                return {"type": "message", "text": activity.get("text", "")}
            elif activity["type"] == "endOfConversation":
                return {"type": "endOfConversation"}
    except Exception as ex:
        app.logger.error(f"Error parsing bot activity: {ex}")
    return {"type": "error", "text": "Something went wrong"}

async def play_to_all(call_media, message):
    ssml_source = SsmlSource(f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'><voice name='en-US-NancyNeural'>{message}</voice></speak>")
    play_options = PlayToAllOptions(ssml_source)
    await call_media.play_to_all(play_options)

if __name__ == "__main__":
    app.run(port=8080)