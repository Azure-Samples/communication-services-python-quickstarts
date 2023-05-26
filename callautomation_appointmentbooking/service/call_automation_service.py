from azure.communication.callautomation import (
    CallAutomationClient,
    CallConnectionClient,
    ServerCallLocator,
    PhoneNumberIdentifier,
    RecognizeInputType,
    DtmfTone)
from azure.core.exceptions import AzureError
from flask import current_app as app, Response, json
from core import constants
from core.config import Config
from callautomation_appointmentbooking.exception.call_automation_exception import CallAutomationException


class CallAutomationService:
    def __init__(self, call_connection_id):
        self.call_connection_id = call_connection_id
        self.call_connection = CallConnectionClient.from_connection_string(Config.ACS_CONNECTION_STRING, call_connection_id)
        self.call_automation = CallAutomationClient.from_connection_string(Config.ACS_CONNECTION_STRING)


    def validate_subscription(self, event):
        app.logger.info("Validating subscription")
        validation_code = event.data['validationCode']
        validation_response = {'validationResponse': validation_code}
        return validation_response

    def answer_call(self, event):
        try:
            app.logger.info("Answering call")
            caller_id = event.data["from"]["rawId"]
            incoming_call_context = event.data['incomingCallContext']
            event_callback_uri = Config.BASE_CALLBACK_URI + "api/event?callerId=" + caller_id
            call_connection_properties = self.call_automation.answer_call(incoming_call_context, event_callback_uri)
            return call_connection_properties
        except AzureError as ae:
            app.logger.error("Exception raised while answering call, %s", str(ae))
            raise CallAutomationException(ae)

    def start_recording(self):
        try:
            app.logger.info("Starting recording for call connection id %s", self.call_connection_id)
            server_call_id = self.call_connection.get_call_properties().server_call_id
            recording_properties = self.call_automation.start_recording(call_locator=ServerCallLocator(server_call_id))
            return recording_properties
        except AzureError as ae:
            app.logger.error("Exception raised while starting the recording, %s", str(ae))
            raise CallAutomationException(ae)

    def play_audio(self, file_source, operation_context):
        try:
            app.logger.info("Playing audio in call with connection id %s", self.call_connection_id)
            self.call_connection.play_media_to_all(file_source, operation_context=operation_context)
        except AzureError as ae:
            app.logger.error("Exception raised while playing audio, %s", str(ae))
            raise CallAutomationException(ae)

    def single_digit_dtmf_recognition(self, caller_id, file_source):
        try:
            app.logger.info("Recognizing DTMF for call with connection id %s", self.call_connection_id)
            target_participant = PhoneNumberIdentifier(caller_id)
            self.call_connection.start_recognizing_media(input_type=RecognizeInputType.DTMF,
                                                         target_participant=target_participant,
                                                         play_prompt=file_source,
                                                         interrupt_prompt=True,
                                                         initial_silence_timeout=10,
                                                         dtmf_inter_tone_timeout=10,
                                                         dtmf_max_tones_to_collect=1,
                                                         dtmf_stop_tones=[DtmfTone.POUND, DtmfTone.ASTERISK])
        except AzureError as ae:
            app.logger.error("Exception raised while starting DTMF recognition, %s", str(ae))
            raise CallAutomationException(ae)

    def parse_choice_from_recognize_event(self, event):
        app.logger.info("Parsing choice from event for call with connection id %s", self.call_connection_id)
        if event.type == constants.RECOGNIZE_COMPLETED_EVENT:
            if len(event.data['collectTonesResult']['tones']) == 1:
                choice = event.data['collectTonesResult']['tones'][0]
                return choice
            else:
                return None
        elif event.type == constants.RECOGNIZE_FAILED_EVENT:
            return None

    def terminate_call(self):
        try:
            app.logger.info("Terminating call with connection id %s", self.call_connection_id)
            self.call_connection.hang_up(is_for_everyone=True)
        except AzureError as ae:
            app.logger.error("Exception raised while terminating call, %s", str(ae))
            raise CallAutomationException(ae)
