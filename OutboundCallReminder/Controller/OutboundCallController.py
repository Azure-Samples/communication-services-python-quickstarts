from aiohttp import web
from EventHandler.EventAuthHandler import EventAuthHandler
from EventHandler.EventDispatcher import EventDispatcher


class OutboundCallController():

    app = web.Application()

    def __init__(self):
        self.app.add_routes(
            [web.post('/api/outboundcall/callback', self.on_incoming_request_async)])
        self.app.add_routes([web.get("/audio/{file_name}", self.load_file)])
        web.run_app(self.app, port=9007)

    async def on_incoming_request_async(self, request):
        param = request.rel_url.query
        content = await request.content.read()

        eventhandler = EventAuthHandler()
        if (param.get('secret') and eventhandler.authorize(param['secret'])):
            eventDispatcher: EventDispatcher = EventDispatcher.get_instance()
            eventDispatcher.process_notification(str(content.decode('UTF-8')))

        return "OK"

    async def load_file(self, request):
        file_name = request.match_info.get('file_name', "Anonymous")
        resp = web.FileResponse(f'audio/{file_name}')
        return resp
