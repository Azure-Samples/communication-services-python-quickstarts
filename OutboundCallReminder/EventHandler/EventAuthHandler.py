from ConfigurationManager import ConfigurationManager
from Logger import Logger


class EventAuthHandler:

    secret_value = None

    def __init__(self):
        configuration = ConfigurationManager.get_instance()
        self.secret_value = configuration.get_app_settings("SecretPlaceholder")

        if (self.secret_value == None or self.secret_value == ''):
            Logger.log_message(Logger.INFORMATION, "SecretPlaceholder is null")
            self.secret_value = "h3llowW0rld"

    def authorize(self, requestSecretValue):
        return ((requestSecretValue != None) and (requestSecretValue == self.secret_value))

    def get_secret_querystring(self):
        secretKey = "secret"
        return (secretKey + "=" + self.secret_value)
