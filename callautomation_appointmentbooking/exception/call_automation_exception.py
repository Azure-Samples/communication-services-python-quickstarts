class CallAutomationException(Exception):
    def __init__(self, error_details):
        super().__init__(str(error_details))
        self.error_details = error_details
