import enum

class Logger(enum.Enum):
    INFORMATION = 1
    ERROR = 2

    @staticmethod
    def log_message(messageType: object, message: str):
        logMessage = messageType.name + " : " + message
        print(logMessage)