import re
import traceback
import uuid
import asyncio
from Utils.Logger import Logger
from Utils.Constants import Constants
from Utils.CommunicationIdentifierKind import CommunicationIdentifierKind
from Utils.CallConfiguration import CallConfiguration
from EventHandler.EventDispatcher import EventDispatcher
from azure.communication.callingserver.aio import CallingServerClient
from azure.communication.callingserver import CallConnectionStateChangedEvent, ToneReceivedEvent, ToneInfo, PlayAudioResultEvent, CallMediaType, CallingEventSubscriptionType, CallConnectionState, CallingOperationStatus, ToneValue, CallingServerEventType, ParticipantsUpdatedEvent, CommunicationUserIdentifier, PhoneNumberIdentifier
# from azure.communication.identity import 

PLAY_AUDIO_AWAIT_TIMER = 10


class IncomingCallHandler:
    _calling_server_client = None
    _call_configuration = None
    _call_connection = None
    _target_participant = None

    _call_established_task: asyncio.Future = None
    _play_audio_completed_task: asyncio.Future = None
    _call_terminatied_task: asyncio.Future = None
    _tone_received_completed_task: asyncio.Future = None
    _transfer_to_participant_complete_task: asyncio.Future = None
    _max_retry_attempt_count = 3

    def __init__(self, calling_server_client: CallingServerClient, call_configuration: CallConfiguration):
        self._call_configuration = call_configuration
        self._calling_server_client = calling_server_client
        self._target_participant = call_configuration.target_participant

    async def report(self, incomming_call_context: str):
        try:
            # wait for 10 sec before answering the call.
            await asyncio.sleep(10)

            # answer call
            response = await self._calling_server_client.answer_call(
                incomming_call_context,
                requested_media_types={CallMediaType.AUDIO},
                requested_call_events={
                    CallingEventSubscriptionType.PARTICIPANTS_UPDATED, CallingEventSubscriptionType.TONE_RECEIVED},
                callback_uri=self._call_configuration.app_callback_url
            )

            Logger.log_message(Logger.INFORMATION,
                               "AnswerCall Response ----->" + str(response))

            self._call_connection = self._calling_server_client.get_call_connection(response.call_connection_id)
            self._register_to_call_state_change_event(
                self._call_connection.call_connection_id)

            # wait for the call to get connected
            await self._call_established_task

            self._register_to_dtmf_result_event(
                self._call_connection.call_connection_id)

            await self._play_audio_async()
            play_audio_completed = await self._play_audio_completed_task

            if(play_audio_completed == False):
                await self._hang_up_async()
            else:
                tone_received_completed_task = await self._tone_received_completed_task
                if(tone_received_completed_task == True):
                    participant: str = self._target_participant
                    Logger.log_message(
                        Logger.INFORMATION, "Transfering call to participant -----> " + participant)
                    transfer_to_participant_completed = await self._transfer_to_participant(participant)
                    if(transfer_to_participant_completed == False):
                        await self._retry_transfer_to_participant_async(participant)
                await self._hang_up_async()
            await self._call_terminatied_task
        except Exception as ex:
            Logger.log_message(Logger.ERROR,
                               "Call ended unexpectedly, reason: " + str(ex))
            raise Exception(
                "Failed to report incoming call --> " + str(ex))

    async def _retry_transfer_to_participant_async(self, participant):
        retry_attempt_count = 1
        while(retry_attempt_count <= self._max_retry_attempt_count):
            Logger.log_message(Logger.INFORMATION,
                               "Retrying Transfer participant attempt " + str(retry_attempt_count) + " is in progress")
            transfer_to_participant_result = await self._transfer_to_participant(participant)
            if(transfer_to_participant_result):
                return
            else:
                Logger.log_message(Logger.INFORMATION,
                                   "Retrying Transfer participant attempt " + str(retry_attempt_count) + " has failed")
                retry_attempt_count += 1

    async def _play_audio_async(self):
        try:
            operation_context = str(uuid.uuid4())
            play_audio_response = await self._call_connection.play_audio(
                audio_url=self._call_configuration.audio_file_uri,
                is_looped=True,
                operation_context=operation_context
            )
            Logger.log_message(Logger.INFORMATION, "PlayAudioAsync response --> " + str(play_audio_response) +  ", Id: " + play_audio_response.operation_id +
                               ", Status: " + play_audio_response.status + ", OperationContext: " + str(play_audio_response.operation_context) + ", ResultInfo: " + str(play_audio_response.result_details))

            if (play_audio_response.status == CallingOperationStatus.RUNNING):
                Logger.log_message(Logger.INFORMATION,
                                   "Play Audio state: " + play_audio_response.status)
                # listen to play audio events
                self._register_to_play_audio_result_event(
                    play_audio_response.operation_context)

                tasks = []
                tasks.append(self._play_audio_completed_task)
                tasks.append(asyncio.create_task(
                    asyncio.sleep(PLAY_AUDIO_AWAIT_TIMER)))

                await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                if (not self._play_audio_completed_task.done()):
                    try:
                        # cancel playing audio
                        await self._cancel_all_media_operations()
                        self._play_audio_completed_task.set_result(True)
                    except Exception as ex:
                        pass
                    try:
                        # After playing audio for 10 sec, make toneReceivedCompleteTask true.
                        self._tone_received_completed_task.set_result(True)
                    except Exception as ex:
                        pass
        except Exception as ex:
            Logger.log_message(
                Logger.ERROR, "Failure occured while playing audio on the call. Exception: " + str(ex))

    async def _hang_up_async(self):
        Logger.log_message(Logger.INFORMATION,
                           "Performing Hangup operation")
        hang_up_response = await self._call_connection.hang_up()
        Logger.log_message(Logger.INFORMATION,
                           "hang_up_async response -----> " + hang_up_response)

    async def _cancel_all_media_operations(self):
        Logger.log_message(Logger.INFORMATION,
                           "Cancellation request, CancelMediaProcessing will be performed")
        await self._call_connection.cancel_all_media_operations()

    def _register_to_call_state_change_event(self, call_leg_id):
        self._call_terminated_task = asyncio.Future()
        self._call_established_task = asyncio.Future()

        # set the callback method
        def call_state_change_notificaiton(call_event):
            try:
                call_state_changes: CallConnectionStateChangedEvent = call_event
                Logger.log_message(
                    Logger.INFORMATION, "Call State changed to -- > " + call_state_changes.call_connection_state)

                if (call_state_changes.call_connection_state == CallConnectionState.CONNECTED):
                    Logger.log_message(Logger.INFORMATION,
                                       "Call State successfully connected")
                    self._call_established_task.set_result(True)

                elif (call_state_changes.call_connection_state == CallConnectionState.DISCONNECTED):
                    EventDispatcher.get_instance().unsubscribe(
                        CallingServerEventType.CALL_CONNECTION_STATE_CHANGED_EVENT, call_leg_id)
                    self._call_terminated_task.set_result(True)

            except asyncio.InvalidStateError:
                pass

        # Subscribe to the event
        EventDispatcher.get_instance().subscribe(CallingServerEventType.CALL_CONNECTION_STATE_CHANGED_EVENT,
                                                 call_leg_id, call_state_change_notificaiton)

    def _register_to_play_audio_result_event(self, operation_context):
        self._play_audio_completed_task = asyncio.Future()

        def play_prompt_response_notification(call_event):
            play_audio_result_event: PlayAudioResultEvent = call_event
            Logger.log_message(
                Logger.INFORMATION, "Play audio status -- > " + str(play_audio_result_event.status))

            if (play_audio_result_event.status == CallingOperationStatus.COMPLETED):
                EventDispatcher.get_instance().unsubscribe(
                    CallingServerEventType.PLAY_AUDIO_RESULT_EVENT, operation_context)
                try:
                    self._play_audio_completed_task.set_result(True)
                except:
                    pass
            elif (play_audio_result_event.status == CallingOperationStatus.FAILED):
                try:
                    self._play_audio_completed_task.set_result(False)
                except:
                    pass

        # Subscribe to event
        EventDispatcher.get_instance().subscribe(CallingServerEventType.PLAY_AUDIO_RESULT_EVENT,
                                                 operation_context, play_prompt_response_notification)

    def _register_to_dtmf_result_event(self, call_leg_id):
        self._tone_received_completed_task = asyncio.Future()

        async def dtmf_received_event(call_event):
            tone_received_event: ToneReceivedEvent = call_event
            tone_info: ToneInfo = tone_received_event.tone_info

            Logger.log_message(Logger.INFORMATION,
                               "Tone received -- > : " + str(tone_info.tone))

            if (tone_info.tone == ToneValue.TONE1):
                try:
                    self._tone_received_completed_task.set_result(True)
                except:
                    pass
            else:
                try:
                    self._tone_received_completed_task.set_result(False)
                except:
                    pass
            EventDispatcher.get_instance().unsubscribe(
                CallingServerEventType.TONE_RECEIVED_EVENT, call_leg_id)
            # cancel playing audio
            await self._cancel_all_media_operations()

        # Subscribe to event
        EventDispatcher.get_instance().subscribe(
            CallingServerEventType.TONE_RECEIVED_EVENT, call_leg_id, dtmf_received_event)

    async def _transfer_to_participant(self, target_participant: str):
        self._transfer_to_participant_complete_task = asyncio.Future()
        identifier_kind = self._get_identifier_kind(target_participant)

        if (identifier_kind == CommunicationIdentifierKind.UNKNOWN_IDENTITY):
            Logger.log_message(Logger.INFORMATION, "Unknown identity provided. Enter valid phone number or communication user id")
            try:
                self._transfer_to_participant_complete_task.set_result(True)
            except:
                pass
        else:
            operation_context = str(uuid.uuid4())
            self._register_to_transfer_participants_result_event(operation_context)
            if (identifier_kind == CommunicationIdentifierKind.USER_IDENTITY):
                identifier = CommunicationUserIdentifier(target_participant)
                response = await self._call_connection.transfer_to_participant(identifier, operation_context = operation_context)
                Logger.log_message(Logger.INFORMATION, "TransferParticipantAsync response --> " + str(response) + ", status: " + response.status
                     + ", OperationContext: " + response.operation_context + ", OperationId: " + response.operation_id + ", ResultDetails: " + str(response.result_details))
            elif (identifier_kind == CommunicationIdentifierKind.PHONE_IDENTITY):
                identifier =  PhoneNumberIdentifier(target_participant)
                response = await self._call_connection.transfer_to_participant(identifier, operation_context = operation_context)
                Logger.log_message(Logger.INFORMATION, "TransferParticipantAsync response --> " + str(response))
        
        transfer_to_participant_completed = await self._transfer_to_participant_complete_task
        return transfer_to_participant_completed


    async def _register_to_transfer_participants_result_event(self, operation_context: str):        
        async def transfer_to_participant_received_event(call_event):
            transfer_to_participant_updated_event: ParticipantsUpdatedEvent = call_event
            if(transfer_to_participant_updated_event != None):
                Logger.log_message(Logger.INFORMATION, "Transfer participant callconnection ID - " + transfer_to_participant_updated_event.call_connection_id)
                EventDispatcher.get_instance().unsubscribe(CallingServerEventType.PARTICIPANTS_UPDATED_EVENT, operation_context)
                Logger.log_message(Logger.INFORMATION, "Sleeping for 60 seconds before proceeding further")
                await asyncio.sleep(60)
                self._transfer_to_participant_complete_task.set_result(True)
            else:
                self._transfer_to_participant_complete_task.set_result(False)
        
        EventDispatcher.get_instance().unsubscribe(CallingServerEventType.ParticipantsUpdatedEvent, operation_context, transfer_to_participant_received_event)

        
    def _get_identifier_kind(self, participant_number: str):
        return CommunicationIdentifierKind.USER_IDENTITY if re.search(Constants.userIdentityRegex.value, participant_number, re.IGNORECASE) else CommunicationIdentifierKind.PHONE_IDENTITY if re.search(Constants.phoneIdentityRegex.value, participant_number, re.IGNORECASE) else CommunicationIdentifierKind.UNKNOWN_IDENTITY