from dataclasses import dataclass
import json
from typing import Optional
from azure.communication.callautomation import (CommunicationIdentifier )
@dataclass

class AudioData:
    def __init__(self, data: str, timestamp: str=None, is_silent: bool=None, participant: Optional[CommunicationIdentifier] = None):
        self.data = data
        self.timestamp = timestamp
        self.is_silent = is_silent
        self.participant = participant

@dataclass
class StopAudio:
    pass

@dataclass
class OutStreamingData:
    def __init__(self, kind: str, audio_data: AudioData, stop_audio: StopAudio =None):
        self.kind = kind
        self.audio_data = audio_data
        self.stop_audio = stop_audio