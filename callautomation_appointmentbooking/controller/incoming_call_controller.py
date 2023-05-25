from azure.eventgrid import EventGridEvent
from flask import request, Blueprint, Response, json
from core.events_handler import EventsHandler

incoming_call_api = Blueprint('incoming_call_api', __name__)


@incoming_call_api.route('/api/incomingCall', methods=['POST'])
def incoming_call_handler():
    for event_dict in request.json:
        event = EventGridEvent.from_dict(event_dict)
        event_handler_response = EventsHandler().handle_incoming_events(event)
        return Response(response=json.dumps(event_handler_response), status=200)
