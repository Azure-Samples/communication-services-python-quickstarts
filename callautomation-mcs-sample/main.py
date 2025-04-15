from quart import Quart, request, Response, websocket
from azure.communication.callautomation import CallAutomationClient, SsmlSource
import os
import asyncio
import requests
from collections import defaultdict
from azure.eventgrid import EventGridEvent, SystemEventNames
from azure.core.messaging import CloudEvent
import websockets

# Flask app setup
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
    app.logger.info(f"Received events")
    return "Hello ACS CallAutomation - MCS Sample!"


@app.route("/api/incomingCall", methods=["POST"])
async def incoming_call():
    event_grid_events = await request.json
    app.logger.info(f"Received events: {event_grid_events}")
    for event_grid_event in event_grid_events:
        event = EventGridEvent.from_dict(event_grid_event)
        if event.event_type == SystemEventNames.EventGridSubscriptionValidationEventName:
            validation_code = event.data["validationCode"]
            # Respond to validation event
            return Response(response=json.dumps({"validationResponse": validation_code}), status=200)

        incoming_call_context = event.data["incomingCallContext"]
        callback_uri = f"{BASE_URI}/api/calls/{uuid.uuid4()}"

        try:
            answer_call_result = await call_automation_client.answer_call(
                incoming_call_context=incoming_call_context,
                callback_url=callback_uri,
                cognitive_services_endpoint=COGNITIVE_SERVICE_ENDPOINT
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

        elif event.type == "Microsoft.Communication.CallDisconnected":
            call_store.pop(correlation_id, None)
    return Response(status=200)

@app.websocket('/ws')
async def websocket_handler():
    # Extract headers
    correlation_id = websocket.headers.get("x-ms-call-correlation-id")
    call_connection_id = websocket.headers.get("x-ms-call-connection-id")

    # Get call media
    call_media = None
    if call_connection_id:
        call_connection = call_automation_client.get_call_connection(call_connection_id)
        call_media = call_connection.get_call_media()

    app.logger.info(f"****************************** Correlation ID: {correlation_id}")
    app.logger.info(f"****************************** Call Connection ID: {call_connection_id}")

    conversation_id = call_store.get(correlation_id, {}).get("conversation_id")

    try:
        partial_data = ""

        while True:
            # Receive data from WebSocket
            data = await websocket.receive()
            if not data:
                break

            try:
                # Handle partial data
                partial_data += data
                if data.endswith("\n"):  # Assuming messages are newline-delimited
                    message = partial_data.strip()
                    partial_data = ""

                    app.logger.info(f"\n[{asyncio.get_event_loop().time()}] {message}")

                    if "Intermediate" in message:
                        app.logger.info("\nCanceling prompt")
                        if call_media:
                            await call_media.cancel_all_media_operations()
                    else:
                        # Parse transcription data
                        transcription_data = json.loads(message)
                        if transcription_data.get("type") == "TranscriptionData":
                            text = transcription_data.get("text", "")
                            app.logger.info(f"\n[{asyncio.get_event_loop().time()}] {text}")

                            if transcription_data.get("resultState") == "Final":
                                if not conversation_id:
                                    conversation_id = call_store.get(correlation_id, {}).get("conversation_id")

                                if conversation_id:
                                    await send_message_to_bot(conversation_id, text)
                                else:
                                    app.logger.info("\nConversation ID is null")
            except Exception as ex:
                app.logger.info(f"Exception while processing WebSocket message: {ex}")
    except Exception as ex:
        app.logger.info(f"WebSocket error: {ex}")
    finally:
        app.logger.info("WebSocket connection closed")

async def start_conversation():
    response = http_client.post("https://directline.botframework.com/v3/directline/conversations")
    response.raise_for_status()
    return response.json()


async def send_message_to_bot(conversation_id, message):
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
    # Remove inline references like [1], [2], etc.
    without_inline_refs = re.sub(r"\[\d+\]", "", input_text)

    # Remove reference list at the end (lines starting with [number]:)
    without_ref_list = re.sub(r"\n\[\d+\]:.*(\n|$)", "", without_inline_refs)

    return without_ref_list.strip()

async def listen_to_bot_websocket(stream_url, call_connection):
    if not stream_url:
        app.logger.info("WebSocket streaming is not enabled for this MCS bot.")
        return

    async with websockets.connect(stream_url) as ws:
        try:
            while True:
                message = await ws.recv()
                bot_activity = extract_latest_bot_activity(message)

                if bot_activity["type"] == "message":
                    app.logger.info(f"\nPlaying Bot Response: {bot_activity['text']}\n")
                    await play_to_all(call_connection.get_call_media(), bot_activity["text"])
                elif bot_activity["type"] == "endOfConversation":
                    app.logger.info("\nEnd of Conversation\n")
                    await call_connection.hang_up()
                    break
        except Exception as ex:
            app.logger.info(f"WebSocket error: {ex}")

def play_to_all(correlation_id, message):
    ssml = f"""
    <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
        <voice name="en-US-NancyNeural">{message}</voice>
    </speak>
    """
    play_source = SsmlSource(ssml)
    call_media = call_automation_client.get_call_connection(correlation_id).get_call_media()
    
    # Use the play_to_all method directly
    call_media.play_to_all(
        play_source=play_source,
        operation_context="Testing"  # Optional: Add context for tracking
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
        app.logger.info(f"Error parsing bot activity: {ex}")
    return {"type": "error", "text": "Something went wrong"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=49412, debug=True)
