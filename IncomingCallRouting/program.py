from Controllers.IncomingCallController import IncomingCallController
from Utils.CallConfiguration import CallConfiguration
from ConfigurationManager import ConfigurationManager
import asyncio

if __name__ == '__main__':
    config_manager = ConfigurationManager.get_instance()
    config = {
        "connection_string": config_manager.get_app_settings("Connectionstring"),
        "app_base_url": config_manager.get_app_settings("BaseUrl"),
        "audio_file_uri": config_manager.get_app_settings("AudioFileUri"),
        "target_participant": config_manager.get_app_settings("TargetParticipant"),
        "bot_identity": config_manager.get_app_settings("BotIdentity")
    }

    loop = asyncio.get_event_loop()
    loop.run_until_complete(IncomingCallController(config))
    
