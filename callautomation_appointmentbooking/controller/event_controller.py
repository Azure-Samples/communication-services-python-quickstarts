from azure.core.messaging import CloudEvent
from flask import request, Blueprint, Response
from core.events_handler import EventsHandler

event_api = Blueprint('event_api', __name__)


@event_api.route('/api/event', methods=['POST'])
def event_handler():
    for event_dict in request.json:
        event = CloudEvent.from_dict(event_dict)
        EventsHandler().handle_callback_events(event)
        return Response(status=200)