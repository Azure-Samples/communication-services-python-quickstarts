from azure.eventgrid import EventGridEvent
from ConfigurationManager import ConfigurationManager
from Logger import Logger
import json
import ast
from aiohttp import web
from azure.core.messaging import CloudEvent
from azure.communication.callautomation import (
    CallAutomationClient, 
    CallInvite, 
    PhoneNumberIdentifier,
    ServerCallLocator)

configuration_manager = ConfigurationManager.get_instance()
connection_string = configuration_manager.get_app_settings("ACSResourceConnectionString")
_client = CallAutomationClient.from_connection_string(connection_string)
_call_connection_id = None
_server_call_id = None
_recording_id = None
_content_location = None
_delete_location = None

class RecordingsController():

    def __init__(self):
        app = web.Application()
        app.add_routes([web.get('/startRecording', RecordingsController.start_recording)])
        app.add_routes([web.get('/pauseRecording', RecordingsController.pause_recording)])
        app.add_routes([web.get('/resumeRecording', RecordingsController.resume_recording)])
        app.add_routes([web.delete('/stopRecording', RecordingsController.stop_recording)])
        app.add_routes([web.get('/getRecordingState', RecordingsController.get_recording_state)])
        app.add_routes([web.get('/downloadRecording', RecordingsController.download_recording)])
        app.add_routes([web.delete('/deleteRecordingFile', RecordingsController.delete_recording)])
        app.add_routes([web.get('/outboundCall', RecordingsController.outbound_call)])
        app.add_routes([web.post('/api/callbacks', RecordingsController.start_callback)])
        app.add_routes([web.post('/recordingFileStatus', RecordingsController.recording_file_status)])
        web.run_app(app, port=58963)

    ## region outbound call - an active call required for recording to start.
    async def outbound_call(request):
        callback_url = configuration_manager.get_app_settings('CallbackUri') + "/api/callbacks"
        targetPhoneNumber = (str)(request.rel_url.query['targetPhoneNumber']).replace(" ", "+")
        target = PhoneNumberIdentifier(targetPhoneNumber)
        caller_id = PhoneNumberIdentifier(configuration_manager.get_app_settings('ACSAcquiredPhoneNumber'))
        call_invite = CallInvite(target=target, source_caller_id_number=caller_id)
        response = _client.create_call(target_participant=call_invite,  callback_url=callback_url)
        global _call_connection_id
        _call_connection_id = response.call_connection_id
        return web.Response(text=response.call_connection_id)

    async def start_recording(request):
        try:
            server_call_id = request.rel_url.query['serverCallId']
            if not server_call_id:
                server_call_id = _server_call_id

            response = _client.start_recording(call_locator=ServerCallLocator(server_call_id))
            global _recording_id
            _recording_id = response.recording_id
            return web.Response(text=response.recording_id)
        except Exception as ex:
            Logger.log_message( Logger.ERROR, "Failed to start server recording --> " + str(ex))
            return web.Response(text=str(ex), status=400)

    async def pause_recording(request):
        try:
            recording_id = request.rel_url.query['recordingId']
            if not recording_id:
                recording_id = _recording_id
            
            res = _client.pause_recording(recording_id=recording_id)
            Logger.log_message(Logger.INFORMATION, "PauseRecording response --> " + str(res))
            return web.Response(text="OK")
        except Exception as ex:
            Logger.log_message(Logger.ERROR, "Failed to pause server recording --> " + str(ex))
            return web.Response(text=str(ex), status=500)

    async def resume_recording(request):
        try:
            recording_id = request.rel_url.query['recordingId']
            if not recording_id:
                recording_id = _recording_id

            res = _client.resume_recording(recording_id=recording_id)
            Logger.log_message(Logger.INFORMATION, "ResumeRecording response --> " + str(res))
            return web.Response(text="Ok")
        except Exception as ex:
            Logger.log_message(Logger.ERROR, "Failed to resume server recording --> " + str(ex))
            return web.Response(text=str(ex), status=500)

    async def stop_recording(request):
        try:
            recording_id = request.rel_url.query['recordingId']
            if not recording_id:
                recording_id = _recording_id

            res = _client.stop_recording(recording_id=recording_id)
            Logger.log_message(Logger.INFORMATION,"StopRecording response --> " + str(res))
            return web.Response(text="Ok")
        except Exception as ex:
            Logger.log_message(Logger.ERROR, "Failed to stop server recording --> " + str(ex))
            return web.Response(text=str(ex), status=500)

    async def get_recording_state(request):
        try:
            recording_id = request.rel_url.query['recordingId']
            if not recording_id:
                recording_id = _recording_id

            res = _client.get_recording_properties(recording_id=recording_id)
            Logger.log_message(Logger.INFORMATION, "GetRecordingState response --> " + str(res))
            return web.Response(text=res.recording_state, status=200)
        except Exception as ex:
            Logger.log_message(Logger.ERROR, "Failed to get recording status --> " + str(ex))
            return web.Response(text=str(ex), status=500)

    async def download_recording(request):
        try:
            recording_data = _client.download_recording(_content_location)
            with open("Recording_File.wav", "wb") as binary_file:
                binary_file.write(recording_data.read())
            return web.Response(text="Ok")
        except Exception as ex:
            Logger.log_message(Logger.ERROR, "Failed to download recording --> " + str(ex))
            return web.Response(text=str(ex), status=500)

    async def delete_recording(request):
     try:
        _client.delete_recording(_delete_location)
        return web.Response(text="Ok")
     except Exception as ex:
        Logger.log_message(Logger.ERROR, "Failed to delete server recording --> " + str(ex))
        return web.Response(text=str(ex), status=500)


    ## region call backs apis
    async def start_callback(request):
        try: 
            content = await request.content.read()
            post_data = str(content.decode('UTF-8'))
            if post_data:
                json_data = ast.literal_eval(json.dumps(post_data))
                event = CloudEvent.from_dict(ast.literal_eval(json_data)[0])
                if event.type == "Microsoft.Communication.CallConnected":
                    global _server_call_id
                    _server_call_id = event.data['serverCallId']
                    Logger.log_message(Logger.INFORMATION, "ServerCallId => "+event.data['serverCallId']) 

        except Exception as ex:
            Logger.log_message(Logger.ERROR, 'Failed to parse callback --> ' + str(ex))
            
    
    # Web hook to receive the recording file update status event, [Do not call directly from Swagger]
    async def recording_file_status(request):
        try:
            content = await request.content.read()
            post_data = str(content.decode('UTF-8'))
            if post_data:
                json_data = ast.literal_eval(json.dumps(post_data))
                event = EventGridEvent.from_dict(ast.literal_eval(json_data)[0])
                Logger.log_message(Logger.INFORMATION,"Event type is  --> " + str(event.event_type))
                Logger.log_message(Logger.INFORMATION,"Request data --> " + str(event.data))

                event_data = event.data
                if event.event_type == 'Microsoft.EventGrid.SubscriptionValidationEvent':
                    subscription_validation_event = event_data
                    code = subscription_validation_event['validationCode']
                    if code:
                        data = {"validationResponse": code}
                        Logger.log_message(Logger.INFORMATION,"Successfully Subscribed EventGrid.ValidationEvent --> " + str(data))
                        return web.Response(body=str(data), status=200)

                if event.event_type == 'Microsoft.Communication.RecordingFileStatusUpdated':
                    acs_recording_file_status_updated_event_data = event_data
                    acs_recording_chunk_info_properties = acs_recording_file_status_updated_event_data['recordingStorageInfo']['recordingChunks'][0]

                    Logger.log_message(Logger.INFORMATION, "acsRecordingChunkInfoProperties response data --> " + str(acs_recording_chunk_info_properties))

                    global _content_location
                    global _delete_location
                    _content_location = acs_recording_chunk_info_properties['contentLocation']
                    _delete_location = acs_recording_chunk_info_properties['deleteLocation']
                    
        except Exception as ex:
            Logger.log_message(Logger.INFORMATION, "Failed to get recording file")
            return web.Response(text='Failed to get recording file', status=400)