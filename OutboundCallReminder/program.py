import asyncio
import nest_asyncio
from azure.communication.identity._shared.models import CommunicationIdentifier
from Controller.OutboundCallController import OutboundCallController
from Logger import Logger
from ConfigurationManager import ConfigurationManager
from CallConfiguration import CallConfiguration
from Ngrok.NgrokService import NgrokService
from azure.communication.identity import CommunicationIdentityClient
from azure.cognitiveservices.speech import AudioDataStream, SpeechConfig, SpeechSynthesizer, SpeechSynthesisOutputFormat
from OutboundCallReminder import OutboundCallReminder


class Program():

    configuration_manager = None
    __ngrok_service = None
    url = "http://localhost:9007"

    def __init__(self):
        Logger.log_message(Logger.INFORMATION, "Starting ACS Sample App ")
        # Get configuration properties
        self.configuration_manager = ConfigurationManager.get_instance()

    async def program(self):
        # Start Ngrok service
        ngrok_url = self.start_ngrok_service()

        try:
            if (ngrok_url and len(ngrok_url)):
                Logger.log_message(Logger.INFORMATION,
                                   "Server started at -- > " + self.url)

                run_sample = asyncio.create_task(self.run_sample(ngrok_url))

                loop = asyncio.get_event_loop()
                loop.run_until_complete(OutboundCallController())
                await run_sample

            else:
                Logger.log_message(Logger.INFORMATION,
                                   "Failed to start Ngrok service")

        except Exception as ex:
            Logger.log_message(
                Logger.ERROR, "Failed to start Ngrok service --> "+str(ex))

        Logger.log_message(Logger.INFORMATION,
                           "Press 'Ctrl + C' to exit the sample")
        self.__ngrok_service.dispose()

    def start_ngrok_service(self):
        try:
            ngrokPath = self.configuration_manager.get_app_settings(
                "NgrokExePath")

            if (not(len(ngrokPath))):
                Logger.log_message(Logger.INFORMATION,
                                   "Ngrok path not provided")
                return None

            Logger.log_message(Logger.INFORMATION, "Starting Ngrok")
            self.__ngrok_service = NgrokService(ngrokPath, None)

            Logger.log_message(Logger.INFORMATION, "Fetching Ngrok Url")
            ngrok_url = self.__ngrok_service.get_ngrok_url()

            Logger.log_message(Logger.INFORMATION,
                               "Ngrok Started with url -- > " + ngrok_url)
            return ngrok_url

        except Exception as ex:
            Logger.log_message(Logger.INFORMATION,
                               "Ngrok service got failed -- > " + str(ex))
            return None

    async def run_sample(self, app_base_url):
        try:

            call_configuration = self.initiate_configuration(app_base_url)
            outbound_call_pairs = self.configuration_manager.get_app_settings(
                "DestinationIdentities")

            if (outbound_call_pairs and len(outbound_call_pairs)):
                identities = outbound_call_pairs.split(";")
                tasks = []
                for identity in identities:
                    pair = identity.split(",")
                    task = asyncio.ensure_future(OutboundCallReminder(
                        call_configuration).report(pair[0].strip(), pair[1].strip()))
                    tasks.append(task)

                _ = await asyncio.gather(*tasks)


            self.delete_user(call_configuration.connection_string,
                            call_configuration.source_identity)

        except Exception as ex:
                Logger.log_message(
                    Logger.ERROR, "Failed to initiate the outbound call Exception -- > " + str(ex))

    # <summary>
    # Fetch configurations from App Settings and create source identity
    # </summary>
    # <param name="app_base_url">The base url of the app.</param>
    # <returns>The <c CallConfiguration object.</returns>

    def initiate_configuration(self, app_base_url):
        connection_string = self.configuration_manager.get_app_settings(
            "Connectionstring")
        source_phone_number = self.configuration_manager.get_app_settings(
            "SourcePhone")

        source_identity = self.create_user(connection_string)
        audio_file_name = self.generate_custom_audio_message()

        return CallConfiguration(connection_string, source_identity, source_phone_number, app_base_url, audio_file_name)

    # <summary>
    # Get .wav Audio file
    # </summary>

    def generate_custom_audio_message(self):
        configuration_manager = ConfigurationManager()
        key = configuration_manager.get_app_settings("CognitiveServiceKey")
        region = configuration_manager.get_app_settings(
            "CognitiveServiceRegion")
        custom_message = configuration_manager.get_app_settings(
            "CustomMessage")

        try:
            if (key and len(key) and region and len(region) and custom_message and len(custom_message)):

                config = SpeechConfig(subscription=key, region=region)
                config.set_speech_synthesis_output_format(
                    SpeechSynthesisOutputFormat["Riff24Khz16BitMonoPcm"])

                synthesizer = SpeechSynthesizer(SpeechSynthesizer=config)

                result = synthesizer.speak_text_async(custom_message).get()
                stream = AudioDataStream(result)
                stream.save_to_wav_file("/audio/custom-message.wav")

                return "custom-message.wav"

            return "sample-message.wav"
        except Exception as ex:
            Logger.log_message(
                Logger.ERROR, "Exception while generating text to speech, falling back to sample audio. Exception -- > " + str(ex))
            return "sample-message.wav"

    # <summary>
    # Create new user
    # </summary>

    def create_user(self, connection_string):
        client = CommunicationIdentityClient.from_connection_string(
            connection_string)
        user: CommunicationIdentifier = client.create_user()
        return user.properties.get('id')

    # <summary>
    # Delete the user
    # </summary>

    def delete_user(self, connection_string, source):
        client = CommunicationIdentityClient.from_connection_string(
            connection_string)
        client.delete_user(source)


if __name__ == "__main__":
    nest_asyncio.apply()
    obj = Program()
    asyncio.run(obj.program())
