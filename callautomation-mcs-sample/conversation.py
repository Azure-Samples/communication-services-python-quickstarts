from typing import Optional

class Conversation:
    def __init__(self, conversation_id: Optional[str] = None, token: Optional[str] = None, 
                 stream_url: Optional[str] = None, reference_grammar_id: Optional[str] = None):
        self.conversation_id = conversation_id
        self.token = token
        self.stream_url = stream_url
        self.reference_grammar_id = reference_grammar_id
