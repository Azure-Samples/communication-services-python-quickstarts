from typing import List
from aiohttp import web
from aiohttp.web_routedef import post
from Logger import Logger
import json
import ast
from CallConfiguration import CallConfiguration
from azure.communication.callingserver import CallingServerClient
from EventHandler.EventAuthHandler import EventAuthHandler
from EventHandler.EventDispatcher import EventDispatcher
from azure.messaging.eventgrid import SystemEvents, EventGridEvent
from Utils.IncomingCallHandler import IncomingCallHandler


class IncomingCallController():

    app = web.Application()

    _calling_server_client: CallingServerClient = None
    _incoming_calls: List = None
    _call_configuration: CallConfiguration = None

    def __init__(self, configuration):
        self.app.add_routes(
            [web.post('/OnIncomingCall', self.on_incoming_call)])
        self.app.add_routes([web.get(
            '/CallingServerAPICallBacks', self.calling_server_api_callbacks)])
        web.run_app(self.app, port=9007)

        self._calling_server_client = CallingServerClient(
            configuration['ResourceConnectionString'])
        self._incoming_calls = []
        self._call_configuration = CallConfiguration.get_call_configuration(
            configuration)

    async def on_incoming_call(self, request):
        try:
            http_content = await request.content.read()
            post_data = str(http_content.decode('UTF-8'))
            if (post_data):
                json_data = ast.literal_eval(json.dumps(post_data))
                cloud_event: EventGridEvent = EventGridEvent.from_dict(
                    ast.literal_eval(json_data)[0])

                if(cloud_event.event_type == 'Microsoft.EventGrid.SubscriptionValidationEvent'):
                    event_data = cloud_event.data
                    code = event_data['validationCode']

                    if (code):
                        response_data = {"validationResponse": code}
                        if(response_data.ValidationResponse != None):
                            return web.Response(body=str(response_data), status=200)
                elif (cloud_event.EventType == 'Microsoft.Communication.IncomingCall'):
                    event_data = str(request)
                    if(event_data != None):
                        incoming_call_context = event_data.split(
                            "\"incomingCallContext\":\"")[1].split("\"}")[0]
                        self._incoming_calls.append(await IncomingCallHandler(self._calling_server_client, self._call_configuration).Report(incoming_call_context))

            return web.Response(status=200)

        except Exception as ex:
            raise Exception("Failed to handle incoming call --> " + str(ex))

    async def calling_server_api_callbacks(self, request, secret: str):
        try:
            eventHandler = EventAuthHandler()
            if EventAuthHandler.authorize(secret):
                if request != None:
                    http_content = await request.content.read()
                    Logger.log_message(
                        Logger.MessageType.INFORMATION, "CallingServerAPICallBacks-------> {request.ToString()}")
                    eventDispatcher: EventDispatcher = EventDispatcher.get_instance()
                    eventDispatcher.process_notification(
                        str(http_content.decode('UTF-8')))
                return web.Response(status=201)
            else:
                return web.Response(status=401)
        except Exception as ex:
            raise Exception(
                "Failed to handle incoming callbacks --> " + str(ex))
