from azure.core.messaging import CloudEvent
from flask import request, Blueprint, Response
from core.events_handler import EventsHandler

event_api = Blueprint('event_api', __name__)

"""
This is controller where it will receive interim events from Call automation service.
We are utilizing event handler, this will handle events and relay to our business logic.
"""
@event_api.route('/api/event', methods=['POST'])
def event_handler():
    for event_dict in request.json:
        event = CloudEvent.from_dict(event_dict)
        EventsHandler().handle_callback_events(event)
        return Response(status=200)
