from quart import Quart, request, Response, websocket
from azure.communication.callautomation import TextSource
from azure.communication.callautomation.aio import CallAutomationClient
from azure.eventgrid import EventGridEvent, SystemEventNames
from azure.core.messaging import CloudEvent
import asyncio
import requests
import websockets
import json
import re
import uuid
from collections import defaultdict
from urllib.parse import urlparse, urlunparse
import os

# Initialize Quart app
app = Quart(__name__)

# Load configuration from environment variables
ACS_CONNECTION_STRING = os.getenv("ACS_CONNECTION_STRING")
COGNITIVE_SERVICE_ENDPOINT = os.getenv("COGNITIVE_SERVICE_ENDPOINT")
DIRECT_LINE_SECRET = os.getenv("DIRECT_LINE_SECRET")
BASE_URI = os.getenv("BASE_URI", "").rstrip("/")
BASE_WSS_URI = BASE_URI.split("https://")[1] if BASE_URI else None

# Initialize Call Automation Client
call_automation_client = CallAutomationClient.from_connection_string(ACS_CONNECTION_STRING)

# Store call contexts
call_store = defaultdict(dict)

# HTTP client for Direct Line
headers = {"Authorization": f"Bearer {DIRECT_LINE_SECRET}"}
http_client = requests.Session()
http_client.headers.update(headers)

@app.route("/", methods=["GET"])
async def home():
    """Home route to verify the service is running."""
    app.logger.info("Received events")
    return "Hello ACS CallAutomation - MCS Sample!"

@app.route("/api/incomingCall", methods=["POST"])
async def incoming_call():
    """
    Handles incoming call events from Azure Event Grid.
    Validates subscription and answers incoming calls.
    """
    app.logger.info("Received incoming call event.")
    try:
        for event_dict in await request.json:
            event = EventGridEvent.from_dict(event_dict)
            app.logger.info("Incoming event data: %s", event.data)

            # Handle subscription validation
            if event.event_type == SystemEventNames.EventGridSubscriptionValidationEventName:
                app.logger.info("Validating subscription")
                validation_code = event.data['validationCode']
                return Response(response=json.dumps({"validationResponse": validation_code}), status=200)

            # Handle incoming call
            if event.event_type == "Microsoft.Communication.IncomingCall":
                app.logger.info("Incoming call received: data=%s", event.data)
                caller_id = event.data['from'].get("phoneNumber", {}).get("value", event.data['from']['rawId'])
                app.logger.info("Incoming call handler caller ID: %s", caller_id)

                incoming_call_context = event.data['incomingCallContext']
                guid = uuid.uuid4()
                callback_uri = f"{BASE_URI}/api/calls/{guid}?callerId={caller_id}"
                app.logger.info(f"Callback URI: {callback_uri}")

                try:
                    answer_call_result = await call_automation_client.answer_call(
                        incoming_call_context=incoming_call_context,
                        cognitive_services_endpoint=COGNITIVE_SERVICE_ENDPOINT,
                        callback_url=callback_uri
                    )
                    app.logger.info(f"Call answered, connection ID: {answer_call_result.call_connection_id}")
                except Exception as e:
                    app.logger.error(f"Failed to answer call: {e}")
                    return Response(status=500)
        return Response(status=200)
    except Exception as ex:
        app.logger.error(f"Error handling incoming call: {ex}")
        return Response(status=500)

@app.route("/api/calls/<context_id>", methods=["POST"])
async def call_events(context_id):
    """
    Handles call events such as CallConnected, PlayCompleted, and CallDisconnected.
    """
    app.logger.info("Received call event.")
    app.logger.info(f"Context ID: {context_id}")
    app.logger.info(f"Request data: {await request.data}")
    cloud_events = await request.json

    for cloud_event in cloud_events:
        event = CloudEvent.from_dict(cloud_event)
        call_connection_id = event.data["callConnectionId"]
        app.logger.info(f"Call connection ID: {call_connection_id}")
        call_connection = call_automation_client.get_call_connection(call_connection_id)
        correlation_id = event.data["correlationId"]

        if event.type == "Microsoft.Communication.CallConnected":
            conversation = await start_conversation()
            conversation_id = conversation["conversationId"]
            call_store[correlation_id]["conversation_id"] = conversation_id

            asyncio.create_task(listen_to_bot_websocket(conversation["streamUrl"], call_connection, call_connection_id))
            await send_message_to_bot(conversation_id, "Hi")

        elif event.type == "Microsoft.Communication.PlayFailed":
            app.logger.info("Play Failed")

        elif event.type == "Microsoft.Communication.PlayCompleted":
            app.logger.info("Play Completed")

        elif event.type == "Microsoft.Communication.CallDisconnected":
            call_store.pop(correlation_id, None)
    return Response(status=200)

@app.websocket('/ws')
async def websocket_handler():
    """
    WebSocket handler for processing transcription data and bot responses.
    """
    correlation_id = websocket.headers.get("x-ms-call-correlation-id")
    call_connection_id = websocket.headers.get("x-ms-call-connection-id")

    app.logger.info(f"Correlation ID: {correlation_id}")
    app.logger.info(f"Call Connection ID: {call_connection_id}")

    conversation_id = call_store.get(correlation_id, {}).get("conversation_id")

    try:
        partial_data = ""

        while True:
            data = await websocket.receive()
            if not data:
                break

            try:
                partial_data += data
                if data.endswith("\n"):
                    message = partial_data.strip()
                    partial_data = ""

                    app.logger.info(f"Received message: {message}")

                    if "Intermediate" in message:
                        app.logger.info("Canceling prompt")
                        if call_connection_id:
                            call_connection = call_automation_client.get_call_connection(call_connection_id)
                            await call_connection.cancel_all_media_operations()
                    else:
                        transcription_data = json.loads(message)
                        if transcription_data.get("type") == "TranscriptionData":
                            text = transcription_data.get("text", "")
                            app.logger.info(f"Transcription text: {text}")

                            if transcription_data.get("resultState") == "Final":
                                if not conversation_id:
                                    conversation_id = call_store.get(correlation_id, {}).get("conversation_id")

                                if conversation_id:
                                    await send_message_to_bot(conversation_id, text)
                                else:
                                    app.logger.info("Conversation ID is null")
            except Exception as ex:
                app.logger.info(f"Exception while processing WebSocket message: {ex}")
    except Exception as ex:
        app.logger.info(f"WebSocket error: {ex}")
    finally:
        app.logger.info("WebSocket connection closed")

async def start_conversation():
    """
    Starts a new conversation with the bot using Direct Line API.
    """
    response = http_client.post("https://directline.botframework.com/v3/directline/conversations")
    response.raise_for_status()
    return response.json()

async def send_message_to_bot(conversation_id, message):
    """
    Sends a message to the bot using Direct Line API.
    """
    payload = {
        "type": "message",
        "from": {"id": "user1"},
        "text": message,
    }
    response = http_client.post(
        f"https://directline.botframework.com/v3/directline/conversations/{conversation_id}/activities",
        json=payload,
    )
    response.raise_for_status()

def extract_latest_bot_activity(raw_message):
    """
    Extracts the latest bot activity from a WebSocket message.
    """
    try:
        activities = json.loads(raw_message).get("activities", [])
        for activity in reversed(activities):
            if activity["type"] == "message" and activity["from"]["id"] != "user1":
                return {"type": "message", "text": remove_references(activity.get("text", ""))}
            elif activity["type"] == "endOfConversation":
                return {"type": "endOfConversation"}
    except Exception as ex:
        app.logger.info(f"Error parsing bot activity: {ex}")
    return {"type": "error", "text": "Something went wrong"}

def remove_references(input_text):
    """
    Removes inline references and reference lists from the input text.
    """
    without_inline_refs = re.sub(r"\[\d+\]", "", input_text)
    without_ref_list = re.sub(r"\n\[\d+\]:.*(\n|$)", "", without_inline_refs)
    return without_ref_list.strip()

async def listen_to_bot_websocket(stream_url, call_connection, call_connection_id):
    """
    Listens to the bot's WebSocket stream and processes bot responses.
    """
    if not stream_url:
        app.logger.info("WebSocket streaming is not enabled for this MCS bot.")
        return

    app.logger.info(f"Connecting to WebSocket: {stream_url}")
    app.logger.info(f"Call Connection ID: {call_connection_id}")
    async with websockets.connect(stream_url) as ws:
        try:
            while True:
                message = await ws.recv()
                bot_activity = extract_latest_bot_activity(message)

                if bot_activity["type"] == "message":
                    app.logger.info(f"Playing Bot Response: {bot_activity['text']}")
                    await play_to_all(call_connection_id, bot_activity["text"])
                elif bot_activity["type"] == "endOfConversation":
                    app.logger.info("End of Conversation")
                    await call_connection.hang_up()
                    break
        except Exception as ex:
            app.logger.info(f"WebSocket error: {ex}")

async def play_to_all(correlation_id, message):
    """
    Plays a message to all participants in the call.
    """
    app.logger.info(f"Playing message: {message}")
    play_source = TextSource(text=message, voice_name="en-US-NancyNeural")
    app.logger.info(f"Play source: {play_source}")
    call_media = call_automation_client.get_call_connection(correlation_id)

    await call_media.play_media_to_all(
        play_source=play_source,
        operation_context="Testing"
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=49412, debug=True)