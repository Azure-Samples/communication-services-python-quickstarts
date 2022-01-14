import json
import ast
from typing import List
from aiohttp import web
from aiohttp.web_routedef import post
from Utils.Logger import Logger
from Utils.CallConfiguration import CallConfiguration
from azure.communication.callingserver.aio import CallingServerClient
from azure.eventgrid import EventGridEvent
from EventHandler.EventAuthHandler import EventAuthHandler
from EventHandler.EventDispatcher import EventDispatcher
from azure.core.messaging import CloudEvent
from Utils.IncomingCallHandler import IncomingCallHandler


class IncomingCallController:

    app = web.Application()

    _calling_server_client: CallingServerClient = None
    _incoming_calls: List = None
    _call_configuration: CallConfiguration = None

    def __init__(self, configuration):
        self._call_configuration = CallConfiguration.get_call_configuration(
            configuration)
        self._calling_server_client = CallingServerClient.from_connection_string(
            self._call_configuration.connection_string)
        self._incoming_calls = []
        self.app.add_routes(
            [web.post('/OnIncomingCall', self.on_incoming_call)])
        self.app.add_routes([web.post(
            '/CallingServerAPICallBacks', self.calling_server_api_callbacks)])
        web.run_app(self.app, port=9007)


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
                        response_data = {"ValidationResponse": code}
                        if(response_data["ValidationResponse"] != None):
                            return web.Response(body=str(response_data), status=200)
                elif (cloud_event.event_type == 'Microsoft.Communication.IncomingCall'):
                    if(post_data != None and cloud_event.data["to"]['rawId'] == self._call_configuration.bot_identity):
                        incoming_call_context = post_data.split(
                            "\"incomingCallContext\":\"")[1].split("\"}")[0]
                        self._incoming_calls.append(await IncomingCallHandler(self._calling_server_client, self._call_configuration).report(incoming_call_context))

            return web.Response(status=200)

        except Exception as ex:
            raise Exception("Failed to handle incoming call --> " + str(ex))

    async def calling_server_api_callbacks(self, request):
        try:
            event_handler = EventAuthHandler()
            param = request.rel_url.query
            if (param.get('secret') and event_handler.authorize(param['secret'])):
                if (request != None):
                    http_content = await request.content.read()
                    Logger.log_message(
                        Logger.INFORMATION, "CallingServerAPICallBacks -------> " + str(request))
                    eventDispatcher: EventDispatcher = EventDispatcher.get_instance()
                    eventDispatcher.process_notification(
                        str(http_content.decode('UTF-8')))
                return web.Response(status=201)
            else:
                return web.Response(status=401)
        except Exception as ex:
            raise Exception(
                "Failed to handle incoming callbacks --> " + str(ex))
