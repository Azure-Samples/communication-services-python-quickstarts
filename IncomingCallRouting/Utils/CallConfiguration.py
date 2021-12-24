from EventHandler.EventAuthHandler import EventAuthHandler


class CallConfiguration:
    callConfiguration = None

    def __init__(self, connection_string, app_base_url, audio_file_name, participant):
        self.connection_string: str = str(connection_string)
        self.app_base_url: str = str(app_base_url)
        self.audio_file_name: str = str(audio_file_name)
        eventhandler = EventAuthHandler()
        self.app_callback_url: str = app_base_url + \
            "/CallingServerAPICallBacks?" + eventhandler.get_secret_querystring()
        self.audio_file_url: str = app_base_url + "/audio/" + audio_file_name
        self.targetParticipant: str = str(participant)

    def get_call_configuration(self, configuration):
        if(self.callConfiguration != None):
            self.callConfiguration = CallConfiguration(
                self, configuration['connection_string'],
                configuration['app_base_url'],
                configuration['audio_file_name'],
                configuration['participant'])

        return self.callConfiguration
