import re
import traceback
import uuid
import asyncio
from Utils.Logger import Logger
from Utils.Constants import Constants
from Utils.CommunicationIdentifierKind import CommunicationIdentifierKind
from Utils.CallConfiguration import CallConfiguration
from EventHandler.EventDispatcher import EventDispatcher
from azure.communication.callingserver.aio import *
from azure.communication.callingserver import *
from azure.communication.identity._shared.models import *

# #CallingServerClient, CancellationTokenSource, CallConnection, CallConnectionStateChangedEvent, ToneReceivedEvent, ToneInfo, PlayAudioResultEvent, AddParticipantResultEvent, CallMediaType, CallingEventSubscriptionType, CreateCallOptions, CallConnectionState, CallingOperationStatus, ToneValue, PlayAudioOptions, CallingServerEventType, PlayAudioResult, AddParticipantResult
PLAY_AUDIO_AWAIT_TIMER = 10


class IncomingCallHandler:
    _calling_server_client = None
    _call_configuration = None
    _call_connection = None
    _report_cancellation_token_source = None
    _report_cancellation_token = None
    _target_participant = None

    _call_estabished_task: asyncio.Future = None
    _play_audio_completed_task: asyncio.Future = None
    _call_terminatied_task: asyncio.Future = None
    _tone_received_completed_task: asyncio.Future = None
    _transfer_to_participant_complete_task: asyncio.Future = None
    _max_retry_attempt_count = 3

    def __init__(self, calling_server_client: CallingServerClient, call_configuration: CallConfiguration):
        self._call_configuration = call_configuration
        self._calling_server_client = calling_server_client
        self._target_participant = call_configuration.targetParticipantpython

    async def report(self, incomming_call_context: str):
        self._report_cancellation_token_source = CancellationTokenSource()
        self._report_cancellation_token = self._report_cancellation_token_source.Token

        try:
            # wait for 10 sec before answering the call.
            await asyncio.sleep(10 * 1000)

            # answer call
            response = await self._calling_server_client.answer_call(
                self._incoming_call_context,
                requested_media_types={CallMediaType.AUDIO},
                requested_call_events={
                    CallingEventSubscriptionType.PARTICIPANTS_UPDATED, CallingEventSubscriptionType.TONE_RECEIVED},
                callback_uri=self._call_configuration.appCallbackUrl
            )

            Logger.log_message(Logger.MessageType.INFORMATION,
                               "AnswerCall Response ----->", response.ToString())

            self._call_connection = response.value
            register_to_call_state_change_event(
                self._call_connection.call_connection_id)

            # wait for the call to get connected
            await self._call_estabished_task()

            register_to_dtmf_result_event(
                self._call_connection.callConnectionId)

            await self.play_audio_async()
            play_audio_completed = await self._play_audio_completed_task

            if(play_audio_completed == False):
                await hang_up_async()
            else:
                tone_received_completed_task = await self._tone_received_completed_task()
                if(tone_received_completed_task == True):
                    participant: str = self._target_participant
                    Logger.log_message(
                        Logger.MessageType.INFORMATION, "Transfering call to participant ----->", participant)
                    transfer_to_participant_completed = await transfer_to_participant(participant)
                    if(transfer_to_participant_completed == False):
                        await retry_transfer_to_participant_async(participant)
                await hang_up_async()
            await self._call_termination_task()
        except Exception as ex:
            Logger.log_message(Logger.MessageType.ERROR,
                               "Call ended unexpectedly, reason:: ", str(ex))
            raise Exception(
                "Failed to report incoming call --> " + str(ex))

    async def retry_transfer_to_participant_async(self, participant):
        retry_attempt_count = 1
        while(retry_attempt_count <= self._max_retry_attempt_count):
            Logger.log_message(Logger.MessageType.INFORMATION,
                               "Retrying Transfer participant attempt ", retry_attempt_count, " is in progress")
            transfer_to_participant_result = await transfer_to_participant(participant)
            if(transfer_to_participant_result):
                return
            else:
                Logger.log_message(Logger.MessageType.INFORMATION,
                                   "Retrying Transfer participant attempt ", retry_attempt_count, " has failed")
                retry_attempt_count += 1

    async def play_audio_async(self):
        try:
            operation_context = str(uuid.uuid4())
            play_audio_response = await self._call_connection.play_audio(
                audio_url=self._call_configuration.audio_file_url,
                is_looped=True,
                operation_context=operation_context
            )
            Logger.log_message(Logger.MesMessageTypes.INFORMATION, "PlayAudioAsync response --> ", response.GetRawResponse(), ", Id: ", response.Value.OperationId,
                               ", Status: ", response.Value.Status, ", OperationContext: ", response.Value.OperationContext, ", ResultInfo: ", response.Value.ResultDetails)

            if (play_audio_response.Value.Status == CallingOperationStatus.Running):
                Logger.log_message(Logger.MessageType.INFORMATION,
                                   "Play Audio state: ", response.Value.Status)
                # listen to play audio events
                self.register_to_play_audio_result_event(
                    play_audio_response.operation_context)

                tasks = []
                tasks.append(self.play_audio_completed_task)
                tasks.append(asyncio.create_task(
                    asyncio.sleep(PLAY_AUDIO_AWAIT_TIMER)))

                await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                if (not self.play_audio_completed_task.done()):
                    try:
                        self.play_audio_completed_task.set_result(True)
                    except Exception as ex:
                        pass
                    try:
                        # After playing audio for 10 sec, make toneReceivedCompleteTask true.
                        self.tone_received_complete_task.set_result(True)
                    except Exception as ex:
                        pass
        except TaskCanceledException as tce:
            Logger.log_message(Logger.MessageType.ERROR,
                               "Play audio operation cancelled")
        except Exception as ex:
            Logger.log_message(
                Logger.MessageType.ERROR, "Failure occured while playing audio on the call. Exception: ", str(ex))

    async def hang_up_async(self):
        if(self._report_cancellation_token.isCancellationRequested):
            Logger.log_message(Logger.MessageType.INFORMATION,
                               "Cancellation request, Hangup will not be performed")
            return
        Logger.log_message(Logger.MessageType.INFORMATION,
                           "Performing Hangup operation")
        hang_up_response = await self._call_connection.hang_up_async(self._report_cancellation_token)
        Logger.log_message(Logger.MessageType.INFORMATION,
                           "hang_up_async response -----> ", hang_up_response)

    async def cancel_all_media_operations(self):
        if(self._report_cancellation_token.isCancellationRequested):
            Logger.log_message(Logger.MessageType.INFORMATION,
                               "Cancellation request, CancelMediaProcessing will not be performed")
            return
        Logger.log_message(Logger.MessageType.INFORMATION,
                           "Cancellation request, CancelMediaProcessing will not be performed")

        operation_context = str(uuid.uuid4())
        response = await self._call_connection.CancelAllMediaOperationsAsync(operation_context, self._report_cancellation_token)

        Logger.log_message(Logger.MessageType.INFORMATION, "PlayAudioAsync response --> ",
                           response.ContentStream, ",  Id: ", response.Content, ", Status: ", response.Status)

    def register_to_call_state_change_event(self, call_leg_id):
        self.call_terminated_task = asyncio.Future()
        self.call_connected_task = asyncio.Future()

        # set the callback method
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

    def cancel_media_processing(self):
        Logger.log_message(
            Logger.INFORMATION, "Performing cancel media processing operation to stop playing audio")

        self.call_connection.cancel_all_media_operations()

    def register_to_play_audio_result_event(self, operation_context):
        self._play_audio_completed_task = asyncio.Future()

        def play_prompt_response_notification(call_event):
            play_audio_result_event: PlayAudioResultEvent = call_event
            Logger.log_message(
                Logger.INFORMATION, "Play audio status -- > " + str(play_audio_result_event.status))

            if (play_audio_result_event.status == CallingOperationStatus.COMPLETED):
                EventDispatcher.get_instance().unsubscribe(
                    CallingServerEventType.PLAY_AUDIO_RESULT_EVENT, operation_context)
                try:
                    self.play_audio_completed_task.set_result(True)
                except:
                    pass
            elif (play_audio_result_event.status == CallingOperationStatus.FAILED):
                try:
                    self.play_audio_completed_task.set_result(False)
                except:
                    pass

        # Subscribe to event
        EventDispatcher.get_instance().subscribe(CallingServerEventType.PLAY_AUDIO_RESULT_EVENT,
                                                 operation_context, play_prompt_response_notification)

    def register_to_dtmf_result_event(self, call_leg_id):
        self.tone_received_complete_task = asyncio.Future()

        def dtmf_received_event(call_event):
            tone_received_event: ToneReceivedEvent = call_event
            tone_info: ToneInfo = tone_received_event.tone_info

            Logger.log_message(Logger.INFORMATION,
                               "Tone received -- > : " + str(tone_info.tone))

            if (tone_info.tone == ToneValue.TONE1):
                try:
                    self.tone_received_complete_task.set_result(True)
                except:
                    pass
            else:
                try:
                    self.tone_received_complete_task.set_result(False)
                except:
                    pass

            EventDispatcher.get_instance().unsubscribe(
                CallingServerEventType.TONE_RECEIVED_EVENT, call_leg_id)
            # cancel playing audio
            self.cancel_media_processing()

        # Subscribe to event
        EventDispatcher.get_instance().subscribe(
            CallingServerEventType.TONE_RECEIVED_EVENT, call_leg_id, dtmf_received_event)

    def _get_identifier_kind(participant_number: str):
        return CommunicationIdentifierKind.USER_IDENTITY if re.search(Constants.userIdentityRegex, participant_number, re.IGNORECASE) else CommunicationIdentifierKind.PHONE_IDENTITY if re.search(Constants.phoneIdentityRegex, participant_number, re.IGNORECASE) else CommunicationIdentifierKind.UNKNOWN_IDENTITY
