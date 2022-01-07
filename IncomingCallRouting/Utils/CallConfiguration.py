from EventHandler.EventAuthHandler import EventAuthHandler


class CallConfiguration:
    callConfiguration = None

    def __init__(self, connection_string, app_base_url, audio_file_uri, participant):
        self.connection_string: str = str(connection_string)
        self.app_base_url: str = str(app_base_url)
        self.audio_file_uri: str = str(audio_file_uri)
        eventhandler = EventAuthHandler()
        self.app_callback_url: str = app_base_url + \
            "/CallingServerAPICallBacks?" + eventhandler.get_secret_querystring()
        self.target_participant: str = str(participant)

    @classmethod
    def get_call_configuration(cls, configuration):
        if(cls.callConfiguration == None):
            cls.callConfiguration = CallConfiguration(
                configuration["connection_string"],
                configuration["app_base_url"],
                configuration["audio_file_uri"],
                configuration["target_participant"])

        return cls.callConfiguration
