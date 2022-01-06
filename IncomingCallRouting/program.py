from Controllers.IncomingCallController import IncomingCallController
from Utils.CallConfiguration import CallConfiguration
from ConfigurationManager import ConfigurationManager
import asyncio

if __name__ == '__main__':
    config_manager = ConfigurationManager.get_instance()
    config = CallConfiguration(
        config_manager.get_app_settings("Connectionstring"),
        config_manager.get_app_settings("BaseUrl"),
        config_manager.get_app_settings("AudioFileUri"),
        config_manager.get_app_settings("TargetParticipant")
    )

    loop = asyncio.get_event_loop()
    loop.run_until_complete(IncomingCallController(config))
    
