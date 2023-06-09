import configparser

class ConfigurationManager:
    __configuration = None
    __instance = None

    def __init__(self):
        if (self.__configuration == None):
            self.__configuration = configparser.ConfigParser()
            self.__configuration.read('config.ini')

    @staticmethod
    def get_instance():
        if (ConfigurationManager.__instance == None):
            ConfigurationManager.__instance = ConfigurationManager()

        return ConfigurationManager.__instance

    def get_app_settings(self, key):
        if (key != None):
            return self.__configuration.get('DEFAULT', key)
        return None