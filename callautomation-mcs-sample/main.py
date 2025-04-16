from quart import Quart, request, Response, websocket
from azure.communication.callautomation import TranscriptionOptions, TranscriptionTransportType, SsmlSource
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
from logging import INFO
import html

# Initialize Quart app
app = Quart(__name__)

# Load configuration from environment variables
ACS_CONNECTION_STRING = os.getenv("ACS_CONNECTION_STRING")
COGNITIVE_SERVICE_ENDPOINT = os.getenv("COGNITIVE_SERVICE_ENDPOINT")
DIRECT_LINE_SECRET = os.getenv("DIRECT_LINE_SECRET")
BASE_URI = os.getenv("BASE_URI", "").rstrip("/")
BASE_WSS_URI = BASE_URI.split("https://")[1] if BASE_URI else None
LOCALE="en-US"

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

            # Handle subscription validation
            if event.event_type == SystemEventNames.EventGridSubscriptionValidationEventName:
                app.logger.info("Validating subscription")
                validation_code = event.data['validationCode']
                return Response(response=json.dumps({"validationResponse": validation_code}), status=200)

            # Handle incoming call
            if event.event_type == "Microsoft.Communication.IncomingCall":
                caller_id = event.data['from'].get("phoneNumber", {}).get("value", event.data['from']['rawId'])
                app.logger.info("Incoming call handler caller ID: %s", caller_id)

                incoming_call_context = event.data['incomingCallContext']
                guid = uuid.uuid4()
                callback_uri = f"{BASE_URI}/api/calls/{guid}?callerId={caller_id}"
                websocket_url = urlunparse(("wss", urlparse(BASE_URI).netloc, "/ws", "", "", ""))
                transcription_config = TranscriptionOptions(
                    transport_url=websocket_url,
                    transport_type=TranscriptionTransportType.WEBSOCKET,
                    locale=LOCALE,
                    start_transcription=True
                )

                try:
                    answer_call_result = await call_automation_client.answer_call(
                        incoming_call_context=incoming_call_context,
                        cognitive_services_endpoint=COGNITIVE_SERVICE_ENDPOINT,
                        callback_url=callback_uri,
                        transcription=transcription_config
                    )
                    app.logger.info("Call answered, connection ID: %s", answer_call_result.call_connection_id)
                except Exception as e:
                    app.logger.error("Failed to answer call: %s", e)
                    return Response(status=500)
        return Response(status=200)
    except Exception as ex:
        app.logger.error("Error handling incoming call: %s", ex)
        return Response(status=500)

@app.route("/api/calls/<context_id>", methods=["POST"])
async def call_events(context_id):
    """
    Handles call events such as CallConnected, PlayCompleted, and CallDisconnected.
    """
    app.logger.info("Received call event.")
    cloud_events = await request.json

    for cloud_event in cloud_events:
        event = CloudEvent.from_dict(cloud_event)
        call_connection_id = event.data["callConnectionId"]
        app.logger.info("Call connection ID: %s", call_connection_id)
        correlation_id = event.data["correlationId"]

        if event.type == "Microsoft.Communication.CallConnected":
            app.logger.info("Call connected event received.")
            conversation = await start_conversation()
            conversation_id = conversation["conversationId"]
            call_store[correlation_id]["conversation_id"] = conversation_id
            call_properties = await call_automation_client.get_call_connection(call_connection_id).get_call_properties()
            app.logger.info("Transcription subscription: %s", call_properties.transcription_subscription)
            
            asyncio.create_task(listen_to_bot_websocket(conversation["streamUrl"], call_connection_id))
            await send_message_to_bot(conversation_id, "Hi")

        elif event.type == "Microsoft.Communication.RecognizeCompleted":
            app.logger.info("Recognize Completed event received.")

        elif event.type == "Microsoft.Communication.TranscriptionStarted":
            app.logger.info("Transcription Started event received.")
        
        elif event.type == "Microsoft.Communication.TranscriptionCompleted":
            app.logger.info("Transcription Completed event received.")

        elif event.type == "Microsoft.Communication.PlayFailed":
            app.logger.info("Play Failed event received.")
            result_info = event.data['resultInformation']
            app.logger.info("Code: %s, Subcode: %s", result_info['code'], result_info['subCode'])
            app.logger.info("Message: %s", result_info['message'])

        elif event.type == "Microsoft.Communication.PlayCompleted":
            app.logger.info("Play Completed event received.")
            context=event.data['operationContext']
            app.logger.info("Context: %s", context)

        elif event.type == "Microsoft.Communication.PlayStarted":
            app.logger.info("Play Started event received.")

        elif event.type == "Microsoft.Communication.CallDisconnected":
            app.logger.info("Call Disconnected event received.")
            call_store.pop(correlation_id, None)
    return Response(status=200)

@app.websocket('/ws')
async def websocket_handler():
    """
    WebSocket handler for processing transcription data and bot responses.
    """
    correlation_id = websocket.headers.get("x-ms-call-correlation-id")
    call_connection_id = websocket.headers.get("x-ms-call-connection-id")

    app.logger.info("Correlation ID: %s", correlation_id)
    app.logger.info("Call Connection ID: %s", call_connection_id)

    conversation_id = call_store.get(correlation_id, {}).get("conversation_id")

    # Get call connection
    call_connection = None
    if call_connection_id:
        call_connection = call_automation_client.get_call_connection(call_connection_id)

    try:
        while True:
            data = await websocket.receive()
            if not data:
                break

            app.logger.info("Received raw WebSocket message: %s", data)

            try:
                message = data.strip()

                app.logger.info("Processed WebSocket message: %s", message)
                if "Intermediate" in message:
                    print("\nCanceling prompt")
                    if call_connection:
                        await call_connection.cancel_all_media_operations()
                else:
                    transcription_data = json.loads(message)
                    if transcription_data.get("kind") == "TranscriptionData":
                        transcription = transcription_data.get("transcriptionData", {})
                        text = transcription.get("text", "")
                        result_status = transcription.get("resultStatus", "")

                        app.logger.info("Transcription text: %s", text)
                        app.logger.info("Transcription result status: %s", result_status)

                        if result_status == "Final":
                            if not conversation_id:
                                conversation_id = call_store.get(correlation_id, {}).get("conversation_id")

                            if conversation_id:
                                await send_message_to_bot(conversation_id, text)
                                app.logger.info("Sent transcription to bot: %s", text)
                            else:
                                app.logger.info("Conversation ID is null")
            except Exception as ex:
                app.logger.info("Exception while processing WebSocket message: %s", ex)
    except Exception as ex:
        app.logger.info("WebSocket error: %s", ex)
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
    app.logger.info("Sending message to bot: %s", message)
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
    app.logger.info("Message sent successfully.")

def extract_latest_bot_activity(raw_message):
    """
    Extracts the latest bot activity from a WebSocket message.
    """
    if not raw_message.strip():
        app.logger.info("Received an empty message.")
        return {"type": "error", "text": "Empty message received"}

    try:
        activities = json.loads(raw_message).get("activities", [])
        for activity in reversed(activities):
            if activity["type"] == "message" and activity["from"]["id"] != "user1":
                return {"type": "message", "text": remove_references(activity.get("text", ""))}
            elif activity["type"] == "endOfConversation":
                return {"type": "endOfConversation"}
    except json.JSONDecodeError as ex:
        app.logger.info(f"JSON decoding error: {ex}")
    except Exception as ex:
        app.logger.info(f"Unexpected error: {ex}")

    return {"type": "error", "text": "Invalid or unrecognized message format"}

def remove_references(input_text):
    """
    Removes inline references and reference lists from the input text.
    """
    without_inline_refs = re.sub(r"\[\d+\]", "", input_text)
    without_ref_list = re.sub(r"\n\[\d+\]:.*(\n|$)", "", without_inline_refs)
    return without_ref_list.strip()

async def listen_to_bot_websocket(stream_url, call_connection_id):
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
                    await call_automation_client.get_call_connection(call_connection_id).hang_up(is_for_everyone=True)
                    break
        except Exception as ex:
            app.logger.info(f"WebSocket error: {ex}")

async def play_to_all(correlation_id, message):
    """
    Plays a message to all participants in the call using SSML.
    """
    if not message.strip():
        app.logger.warning("Cannot play an empty message. Skipping playback.")
        return

    app.logger.info(f"Playing message: {message}")

    # Escape special characters in the message
    escaped_message = html.escape(message)

    # Create an SSML source
    ssml_template = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US"><voice name="en-US-NancyNeural">{escaped_message}</voice></speak>"""
    app.logger.info(f"Generated SSML: {ssml_template}")

    try:
        play_source = SsmlSource(ssml_text=ssml_template)
        call_media = call_automation_client.get_call_connection(correlation_id)

        await call_media.play_media_to_all(
            play_source=play_source,
            operation_context="Testing"
        )
    except Exception as ex:
        app.logger.error(f"Error playing message: {ex}")

if __name__ == "__main__":
    app.logger.setLevel(INFO)
    app.run(port=8080)