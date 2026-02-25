from typing import Optional

class CallContext:
    def __init__(self, correlation_id: Optional[str] = None, conversation_id: Optional[str] = None):
        self.correlation_id = correlation_id
        self.conversation_id = conversation_id
