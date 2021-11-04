from uuid import UUID
from datetime import datetime
from typing import List, Any


class Participant:
    participantId: str

    def __init__(self, participantId: str) -> None:
        self.participantId = participantId


class AudioConfiguration:
    sampleRate: int
    bitRate: int
    channels: int

    def __init__(self, sampleRate: int, bitRate: int, channels: int) -> None:
        self.sampleRate = sampleRate
        self.bitRate = bitRate
        self.channels = channels


class VideoConfiguration:
    longerSideLength: int
    shorterSideLength: int
    framerate: int
    bitRate: int

    def __init__(self, longerSideLength: int, shorterSideLength: int, framerate: int, bitRate: int) -> None:
        self.longerSideLength = longerSideLength
        self.shorterSideLength = shorterSideLength
        self.framerate = framerate
        self.bitRate = bitRate


class RecordingInfo:
    contentType: str
    channelType: str
    format: str
    audioConfiguration: AudioConfiguration
    videoConfiguration: VideoConfiguration

    def __init__(self, contentType: str, channelType: str, format: str, audioConfiguration: AudioConfiguration, videoConfiguration: VideoConfiguration) -> None:
        self.contentType = contentType
        self.channelType = channelType
        self.format = format
        self.audioConfiguration = audioConfiguration
        self.videoConfiguration = videoConfiguration


class Root:
    resourceId: UUID
    callId: UUID
    chunkDocumentId: str
    chunkIndex: int
    chunkStartTime: datetime
    chunkDuration: float
    pauseResumeIntervals: List[Any]
    recordingInfo: RecordingInfo
    participants: List[Participant]

    def __init__(self, resourceId: UUID, callId: UUID, chunkDocumentId: str, chunkIndex: int, chunkStartTime: datetime, chunkDuration: float, pauseResumeIntervals: List[Any], recordingInfo: RecordingInfo, participants: List[Participant]) -> None:
        self.resourceId = resourceId
        self.callId = callId
        self.chunkDocumentId = chunkDocumentId
        self.chunkIndex = chunkIndex
        self.chunkStartTime = chunkStartTime
        self.chunkDuration = chunkDuration
        self.pauseResumeIntervals = pauseResumeIntervals
        self.recordingInfo = recordingInfo
        self.participants = participants
