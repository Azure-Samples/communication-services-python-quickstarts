from dataclasses import dataclass
import json
from typing import Optional
from azure.communication.callautomation import (CommunicationIdentifier )

@dataclass
class AudioData:
    data: str
    timestamp: Optional[str] = None
    is_silent: Optional[bool] = None
    participant: Optional[CommunicationIdentifier] = None

@dataclass
class StopAudio:
    pass

@dataclass
class OutStreamingData:
    kind: str
    audio_data: Optional[AudioData]
    stop_audio: Optional[StopAudio] = None