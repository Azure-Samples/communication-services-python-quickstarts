from asyncio.tasks import FIRST_COMPLETED
import re
import traceback
import uuid
import asyncio
from azure.communication.identity._shared.models import CommunicationIdentifier
from CallConfiguration import CallConfiguration
from ConfigurationManager import ConfigurationManager
from Logger import Logger
from CommunicationIdentifierKind import CommunicationIdentifierKind
from EventHandler.EventDispatcher import EventDispatcher
from azure.communication.callingserver._callingserver_client import CallingServerClient
from azure.communication.callingserver._call_connection import CallConnection
from azure.communication.identity import CommunicationUserIdentifier
from azure.communication.chat import PhoneNumberIdentifier
from azure.communication.callingserver._models import CallConnectionStateChangedEvent, ToneReceivedEvent, \
    ToneInfo, PlayAudioResultEvent, AddParticipantResultEvent, MediaType, EventSubscriptionType,\
    CreateCallOptions, CallConnectionState, OperationStatus, ToneValue, PlayAudioOptions, \
    CallingServerEventType, CancelAllMediaOperationsResult, PlayAudioResult, AddParticipantResult

PLAY_AUDIO_AWAIT_TIMER = 30
ADD_PARTICIPANT_AWAIT_TIMER = 60


class OutboundCallReminder:
    call_configuration: CallConfiguration = None
    calling_server_client: CallingServerClient = None
    call_connection: CallConnection = None

    call_connected_task: asyncio.Future = None
    play_audio_completed_task: asyncio.Future = None
    call_terminated_task: asyncio.Future = None
    tone_received_complete_task: asyncio.Future = None
    add_participant_complete_task: asyncio.Future = None
    max_retry_attempt_count: int = None

    user_identity_regex: str = "8:acs:[0-9a-fA-F]{8}\\-[0-9a-fA-F]{4}\\-[0-9a-fA-F]{4}\\-[0-9a-fA-F]{4}\\-[0-9a-fA-F]{12}_[0-9a-fA-F]{8}\\-[0-9a-fA-F]{4}\\-[0-9a-fA-F]{4}\\-[0-9a-fA-F]{4}\\-[0-9a-fA-F]{12}"
    phone_identity_regex: str = "^\\+\\d{10,14}$"

    def __init__(self, call_configuration):

        self.call_configuration = call_configuration
        self.calling_server_client = CallingServerClient.from_connection_string(
            self.call_configuration.connection_string)
        self.max_retry_attempt_count: int = int(
            ConfigurationManager.get_instance().get_app_settings("MaxRetryCount"))

    async def report(self, target_phone_number, participant):

        try:
            await self.create_call_async(target_phone_number)

            self.register_to_dtmf_result_event(
                self.call_connection.call_connection_id)

            await self.play_audio_async()
            play_audio_completed = await self.play_audio_completed_task

            if (not play_audio_completed):
                self.hang_up_async()
            else:
                try:
                    tone_received_complete = await asyncio.wait_for(self.tone_received_complete_task, timeout=PLAY_AUDIO_AWAIT_TIMER)
                except TimeoutError as ex:
                    Logger.log_message(
                        Logger.INFORMATION, "No response from user in 30 sec, initiating hangup")
                else:
                    if (tone_received_complete):
                        Logger.log_message(Logger.INFORMATION, "Initiating add participant from number --> " +
                                           target_phone_number + " and participant identifier is -- > " + participant)

                        self.add_participant(participant)
                        try:
                            add_participant_completed = await asyncio.wait_for(self.add_participant_complete_task, timeout=ADD_PARTICIPANT_AWAIT_TIMER)
                        except TimeoutError as ex:
                            Logger.log_message(
                                Logger.INFORMATION, "Add participant failed with timeout -- > " + str(ex))
                        else:
                            if (not add_participant_completed):
                                await asyncio.create_task(self.retry_add_participant_async(participant))

                self.hang_up_async()

            # Wait for the call to terminate
            await self.call_terminated_task

        except Exception as ex:
            Logger.log_message(
                Logger.ERROR, "Call ended unexpectedly, reason -- > " + str(ex))
            print(traceback.format_exc())

    async def create_call_async(self, target_phone_number):
        try:
            source = CommunicationUserIdentifier(
                self.call_configuration.source_identity)
            targets = [PhoneNumberIdentifier(target_phone_number)]

            call_modality = [MediaType.AUDIO]
            event_subscription_type = [
                EventSubscriptionType.PARTICIPANTS_UPDATED, EventSubscriptionType.DTMF_RECEIVED]

            options: CreateCallOptions = CreateCallOptions(
                callback_uri=self.call_configuration.app_callback_url, requested_media_types=call_modality, requested_call_events=event_subscription_type)
            options.alternate_Caller_Id = PhoneNumberIdentifier(
                self.call_configuration.source_phone_number)

            Logger.log_message(Logger.INFORMATION,
                               "Performing CreateCall operation")

            self.call_connection = self.calling_server_client.create_call_connection(
                source, targets, options)

            Logger.log_message(
                Logger.INFORMATION, "Call initiated with Call Leg id -- >" + self.call_connection.call_connection_id)

            self.register_to_callstate_change_event(
                self.call_connection.call_connection_id)

            await self.call_connected_task

        except Exception as ex:
            Logger.log_message(
                Logger.ERROR, "Failure occured while creating/establishing the call. Exception -- >" + str(ex))

    def register_to_callstate_change_event(self, call_leg_id):
        self.call_terminated_task = asyncio.Future()
        self.call_connected_task = asyncio.Future()

        # Set the callback method
        def call_state_change_notificaiton(call_event):
            try:
                call_state_changes: CallConnectionStateChangedEvent = call_event
                Logger.log_message(
                    Logger.INFORMATION, "Call State changed to -- > " + call_state_changes.call_connection_state)

                if (call_state_changes.call_connection_state == CallConnectionState.CONNECTED):
                    Logger.log_message(Logger.INFORMATION,
                                       "Call State successfully connected")
                    self.call_connected_task.set_result(True)

                elif (call_state_changes.call_connection_state == CallConnectionState.DISCONNECTED):
                    EventDispatcher.get_instance().unsubscribe(
                        CallingServerEventType.CALL_CONNECTION_STATE_CHANGED_EVENT, call_leg_id)
                    self.call_terminated_task.set_result(True)

            except asyncio.InvalidStateError:
                pass

        # Subscribe to the event
        EventDispatcher.get_instance().subscribe(CallingServerEventType.CALL_CONNECTION_STATE_CHANGED_EVENT,
                                                 call_leg_id, call_state_change_notificaiton)

    def register_to_dtmf_result_event(self, call_leg_id):
        self.tone_received_complete_task = asyncio.Future()

        def dtmf_received_event(call_event):
            tone_received_event: ToneReceivedEvent = call_event
            tone_info: ToneInfo = tone_received_event.tone_info

            Logger.log_message(Logger.INFORMATION,
                               "Tone received -- > : " + str(tone_info.tone))

            if (tone_info.tone == ToneValue.TONE1):
                self.tone_received_complete_task.set_result(True)
            else:
                self.tone_received_complete_task.set_result(False)

            EventDispatcher.get_instance().unsubscribe(
                CallingServerEventType.TONE_RECEIVED_EVENT, call_leg_id)
            # cancel playing audio
            self.cancel_media_processing()

        # Subscribe to event
        EventDispatcher.get_instance().subscribe(
            CallingServerEventType.TONE_RECEIVED_EVENT, call_leg_id, dtmf_received_event)

    def cancel_media_processing(self):
        Logger.log_message(
            Logger.INFORMATION, "Performing cancel media processing operation to stop playing audio")
        operation_context: str = str(uuid.uuid4())

        cancelmediaresponse: CancelAllMediaOperationsResult = self.call_connection.cancel_all_media_operations(
            operation_context=operation_context)

        Logger.log_message(Logger.INFORMATION, "cancelAllMediaOperationsWithResponse -- > Id: " +
                           str(cancelmediaresponse.operation_id) + ", OperationContext: " + str(cancelmediaresponse.operation_context) + ", OperationStatus: " +
                           str(cancelmediaresponse.status))

    async def play_audio_async(self):
        try:
            self.play_audio_completed_task = asyncio.Future()
            # Preparing data for request
            loop = True
            audio_file_uri = self.call_configuration.audio_file_url
            operation_context = str(uuid.uuid4())
            audio_file_id = str(uuid.uuid4())
            callbackuri = self.call_configuration.app_callback_url

            play_audio_options: PlayAudioOptions = PlayAudioOptions(loop=loop,
                                                                    operation_context=operation_context,
                                                                    audio_file_id=audio_file_id,
                                                                    callback_uri=callbackuri)

            Logger.log_message(Logger.INFORMATION,
                               "Performing PlayAudio operation")
            play_audio_response: PlayAudioResult = self.call_connection.play_audio(audio_file_uri=audio_file_uri,
                                                                                   play_audio_options=play_audio_options)

            Logger.log_message(Logger.INFORMATION, "playAudioWithResponse -- > " + str(play_audio_response) +
                               ", Id: " + play_audio_response.operation_id + ", OperationContext: " + play_audio_response.operation_context + ", OperationStatus: " +
                               play_audio_response.status)

            if (play_audio_response.status == OperationStatus.RUNNING):
                Logger.log_message(
                    Logger.INFORMATION, "Play Audio state -- > " + str(OperationStatus.RUNNING))

                # listen to play audio events
                self.register_to_play_audio_result_event(
                    play_audio_response.operation_context)

                tasks = []
                tasks.append(self.play_audio_completed_task)
                tasks.append(asyncio.create_task(
                    asyncio.sleep(PLAY_AUDIO_AWAIT_TIMER)))

                await asyncio.wait(tasks, return_when=FIRST_COMPLETED)

                if(not self.play_audio_completed_task.done()):
                    Logger.log_message(
                        Logger.INFORMATION, "No response from user in 30 sec, initiating hangup")
                    self.play_audio_completed_task.set_result(False)
                    self.tone_received_complete_task.set_result(False)

        except Exception as ex:
            if (self.play_audio_completed_task.cancelled()):
                Logger.log_message(Logger.INFORMATION,
                                   "Play audio operation cancelled")
            else:
                Logger.log_message(
                    Logger.INFORMATION, "Failure occured while playing audio on the call. Exception: " + str(ex))

    def hang_up_async(self):
        Logger.log_message(Logger.INFORMATION, "Performing Hangup operation")

        self.call_connection.hang_up()

    def register_to_play_audio_result_event(self, operation_context):
        def play_prompt_response_notification(call_event):
            play_audio_result_event: PlayAudioResultEvent = call_event
            Logger.log_message(
                Logger.INFORMATION, "Play audio status -- > " + str(play_audio_result_event.status))

            if (play_audio_result_event.status == OperationStatus.COMPLETED):
                EventDispatcher.get_instance().unsubscribe(
                    CallingServerEventType.PLAY_AUDIO_RESULT_EVENT, operation_context)
                self.play_audio_completed_task.set_result(True)
            elif (play_audio_result_event.status == OperationStatus.FAILED):
                self.play_audio_completed_task.set_result(False)

        # Subscribe to event
        EventDispatcher.get_instance().subscribe(CallingServerEventType.PLAY_AUDIO_RESULT_EVENT,
                                                 operation_context, play_prompt_response_notification)

    async def retry_add_participant_async(self, addedParticipant):
        retry_attempt_count: int = 1
        while (retry_attempt_count <= self.max_retry_attempt_count):
            Logger.log_message(Logger.INFORMATION, "Retrying add participant attempt -- > " +
                               str(retry_attempt_count) + " is in progress")
            self.add_participant(addedParticipant)

            try:
                add_participant_result = await asyncio.wait_for(self.add_participant_complete_task, timeout=ADD_PARTICIPANT_AWAIT_TIMER)
            except TimeoutError as ex:
                Logger.log_message(
                    Logger.INFORMATION, "Retry add participant failed with timeout -- > " + str(retry_attempt_count) + str(ex))
            else:
                if (add_participant_result):
                    return
                else:
                    Logger.log_message(
                        Logger.INFORMATION, "Retry add participant attempt -- > " + str(retry_attempt_count) + " has failed")
                    retry_attempt_count = retry_attempt_count + 1

    def add_participant(self, addedParticipant):
        identifier_kind: CommunicationIdentifierKind = self.get_identifier_kind(
            addedParticipant)

        if (identifier_kind == CommunicationIdentifierKind.UNKNOWN_IDENTITY):
            Logger.log_message(
                Logger.INFORMATION, "Unknown identity provided. Enter valid phone number or communication user id")
            return True
        else:
            participant: CommunicationIdentifier = None
            operation_context = str(uuid.uuid4())

            self.register_to_add_participants_result_event(operation_context)

            if (identifier_kind == CommunicationIdentifierKind.USER_IDENTITY):
                participant = CommunicationUserIdentifier(id=addedParticipant)

            elif (identifier_kind == CommunicationIdentifierKind.PHONE_IDENTITY):
                participant = PhoneNumberIdentifier(value=addedParticipant)

            alternate_caller_id = PhoneNumberIdentifier(
                value=str(ConfigurationManager.get_instance().get_app_settings("SourcePhone")))

            add_participant_response: AddParticipantResult = self.call_connection.add_participant(participant=participant,
                                                                                                  alternate_caller_id=alternate_caller_id,
                                                                                                  operation_context=operation_context)
            Logger.log_message(
                Logger.INFORMATION, "addParticipantWithResponse -- > " + add_participant_response.participant_id)

    def register_to_add_participants_result_event(self, operation_context):
        if(self.add_participant_complete_task):
            self.add_participant_complete_task = None

        self.add_participant_complete_task = asyncio.Future()

        def add_participant_received_event(call_event):
            add_participants_updated_event: AddParticipantResultEvent = call_event
            operation_status: OperationStatus = add_participants_updated_event.status
            if (operation_status == OperationStatus.COMPLETED):
                Logger.log_message(
                    Logger.INFORMATION, "Add participant status -- > " + operation_status)
                self.add_participant_complete_task.set_result(True)
            elif(operation_status == OperationStatus.FAILED):
                Logger.log_message(
                    Logger.INFORMATION, "Add participant status -- > " + operation_status)
                self.add_participant_complete_task.set_result(False)

            EventDispatcher.get_instance().unsubscribe(
                CallingServerEventType.ADD_PARTICIPANT_RESULT_EVENT, operation_context)

        # Subscribe to event
        EventDispatcher.get_instance().subscribe(CallingServerEventType.ADD_PARTICIPANT_RESULT_EVENT,
                                                 operation_context, add_participant_received_event)

    def get_identifier_kind(self, participantnumber: str):
        # checks the identity type returns as string
        if(re.search(self.user_identity_regex, participantnumber)):
            return CommunicationIdentifierKind.USER_IDENTITY
        elif(re.search(self.phone_identity_regex, participantnumber)):
            return CommunicationIdentifierKind.PHONE_IDENTITY
        else:
            return CommunicationIdentifierKind.UNKNOWN_IDENTITY
