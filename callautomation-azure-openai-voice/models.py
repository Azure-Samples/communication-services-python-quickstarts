from dataclasses import dataclass
from typing import Optional
from azure.communication.callautomation import (CommunicationIdentifier )
@dataclass
class AudioData:
    data: str
    timestamp: str
    is_silent: bool
    participant: Optional[CommunicationIdentifier]

@dataclass
class StopAudio:
    pass

@dataclass
class OutStreamingData:
    kind: str
    audio_data: AudioData
    stop_audio: StopAudio