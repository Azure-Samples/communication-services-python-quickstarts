from azure.eventgrid import SystemEventNames
from flask import current_app as app, Response, json
from service.appointment_booking_service import AppointmentBookingService
from service.call_automation_service import CallAutomationService


class EventsHandler:
    def handle_incoming_events(self, event):
        app.logger.info("Event received: %s", event.event_type)
        if event.event_type == SystemEventNames.EventGridSubscriptionValidationEventName:
            return CallAutomationService(None).validate_subscription(event)
        elif event.event_type == SystemEventNames.AcsIncomingCallEventName:
            CallAutomationService(None).answer_call(event)
        return None

    def handle_callback_events(self, event):
        call_connection_id = event.data['callConnectionId']
        app.logger.info("Event received: %s, for call connection id:%s", event.type, call_connection_id)
        appointment_booking_service = AppointmentBookingService(call_connection_id)
        appointment_booking_service.invoke_top_level_menu(event)
