import enum
import logging


class Logger(enum.Enum):

    INFORMATION = 1
    ERROR = 2

    @staticmethod
    def log_message(message_type, message):
        log_message = message_type.name + " : " + message
        if message_type == Logger.ERROR:
            logging.error(log_message)
        else:
            logging.info(log_message)
