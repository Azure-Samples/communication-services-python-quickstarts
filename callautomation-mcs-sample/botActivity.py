from typing import Optional

class BotActivity:
    def __init__(self, type: Optional[str] = None, text: Optional[str] = None):
        self.type = type
        self.text = text
