import configparser
from azure.communication.callautomation import FileSource
import logging

config_parser = configparser.RawConfigParser()
config_parser.read("./resources/config.conf")

class Config:
    ACS_CONNECTION_STRING = config_parser.get("APPOINTMENT_BOOKING_CONFIG", "ACS_CONNECTION_STRING")
    BASE_CALLBACK_URI = config_parser.get("APPOINTMENT_BOOKING_CONFIG", "BASE_CALLBACK_URI")
    STATIC_FOLDER = config_parser.get("APPOINTMENT_BOOKING_CONFIG", "STATIC_FOLDER")
    STATIC_URL_PATH = config_parser.get("APPOINTMENT_BOOKING_CONFIG", "STATIC_URL_PATH")

    PROMPT_RECORDING_STARTED = FileSource(BASE_CALLBACK_URI + config_parser.get("APPOINTMENT_BOOKING_CONFIG", "RECORDING_STARTED"))
    PROMPT_MAIN_MENU = FileSource(BASE_CALLBACK_URI + config_parser.get("APPOINTMENT_BOOKING_CONFIG", "MAIN_MENU"))
    PROMPT_CHOICE1 = FileSource(BASE_CALLBACK_URI + config_parser.get("APPOINTMENT_BOOKING_CONFIG", "CHOICE1"))
    PROMPT_CHOICE2 = FileSource(BASE_CALLBACK_URI + config_parser.get("APPOINTMENT_BOOKING_CONFIG", "CHOICE2"))
    PROMPT_CHOICE3 = FileSource(BASE_CALLBACK_URI + config_parser.get("APPOINTMENT_BOOKING_CONFIG", "CHOICE3"))
    PROMPT_RETRY = FileSource(BASE_CALLBACK_URI + config_parser.get("APPOINTMENT_BOOKING_CONFIG", "RETRY"))
    PROMPT_GOODBYE = FileSource(BASE_CALLBACK_URI + config_parser.get("APPOINTMENT_BOOKING_CONFIG", "GOODBYE"))

    LOG_LEVEL = logging.getLevelName(config_parser.get("LOGGING", "LOG_LEVEL"))
