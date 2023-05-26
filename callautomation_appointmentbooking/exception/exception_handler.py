from flask import json
from flask.wrappers import Response
from callautomation_appointmentbooking.exception.call_automation_exception import CallAutomationException


def handle_http_exception(e):
    if isinstance(e.original_exception, CallAutomationException):
        response = Response()
        response.status_code = e.original_exception.error_details.status_code
        response.data = json.dumps({
            "code": e.original_exception.error_details.status_code,
            "name": e.original_exception.error_details.message,
            "description": e.original_exception.error_details.message,
        })
    else:
        response = e.get_response()
        response.data = json.dumps({
            "code": e.code,
            "name": e.name,
            "description": e.description,
        })
    response.content_type = "application/json"
    return response
