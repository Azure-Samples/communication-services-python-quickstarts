from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from azure.core.exceptions import HttpResponseError
from azure.communication.rooms import (
    RoomsClient,
    RoomParticipant,
    RoleType,
    RoomJoinPolicy
)
from azure.communication.identity import CommunicationUserIdentifier
class RoomsQuickstart(object):
    roomsCollection = []
    connection_string = '<connection_string>'
    participant1 = '<communication_identifier>'
    participant2 = '<communication_identifier>'
    participant3 = '<communication_identifier>'
    participant4 = '<communication_identifier>'
    participant5 = '<communication_identifier>'
    participant6 = '<communication_identifier>'

    def setup(self):
        self.rooms_client = RoomsClient.from_connection_string(self.connection_string)
        
    def teardown(self):
        self.delete_all_rooms()
    
    def create_room(self):
        try:
            valid_from = datetime.now(timezone.utc)
            valid_until = valid_from + relativedelta(months=+1,days=+20)
            participants = [RoomParticipant(CommunicationUserIdentifier(self.participant1), RoleType.PRESENTER)]
            participant_1 = RoomParticipant(CommunicationUserIdentifier(self.participant1), RoleType.PRESENTER)
            participant_2 = RoomParticipant(CommunicationUserIdentifier(self.participant2), RoleType.CONSUMER)
            participant_3 = RoomParticipant(CommunicationUserIdentifier(self.participant3), RoleType.ATTENDEE)
            participants = [participant_1, participant_2, participant_3]
            created_room = self.rooms_client.create_room(valid_from, valid_until, RoomJoinPolicy.COMMUNICATION_SERVICE_USERS, participants)
            print('\nRoom created.')
            self.print_room(created_room)
            self.roomsCollection.append(created_room.id)
        except Exception as ex:
            print('Room creation failed.', ex)

    def update_room(self, room_id:str):
        valid_from = datetime.now(timezone.utc)
        valid_until = valid_from + relativedelta(months=+1,days=+1)
        try:
            updated_room = self.rooms_client.update_room(room_id=room_id, valid_from=valid_from, valid_until=valid_until)
            print('\nRoom updated with new valid_from and valid_until time.')
            self.print_room(updated_room)
        except HttpResponseError as ex:
            print(ex)

    def update_participants(self, room_id:str, participants_list:list):
        try:
            participants = []
            for p in participants_list:
                participants.append(RoomParticipant(CommunicationUserIdentifier(p), RoleType.ATTENDEE))
            self.rooms_client.update_participants(room_id, participants)
            print('\nRoom participants updated.')
        except HttpResponseError as ex:
            print(ex)

    def get_room_after_participants_update(self, room_id:str):
        try:
            get_room = self.rooms_client.get_room(room_id=room_id)
            self.print_room(get_room)
        except HttpResponseError as ex:
            print(ex)

    def delete_all_rooms(self):
        for room_id in self.roomsCollection:
            print("\nDeleting room : ", room_id)
            self.rooms_client.delete_room(room_id)

    def print_room(self, room):
        print("\nRoom Id: " + room.id +
              "\nCreated date time: " + str(room.created_date_time) +
              "\nValid From: " + str(room.valid_from) + "\nValid Until: " + str(room.valid_until))
        print("Participants : \n" )
        for i in range(len(room.participants)):
            print(str(i+1), room.participants[i].communication_identifier.properties['id'])

    def get_participants_in_room(self, room_id:str):
        participants = self.rooms_client.get_participants(room_id)
        print('\nParticipants in Room Id :', room_id)
        for i in range(len(participants.participants)):
            print(str(i+1), participants.participants[i].communication_identifier.properties['id'])

    def add_participants_to_room(self, room_id:str, participants_list:list):
        try:
            participants = []
            for p in participants_list:
                participants.append(RoomParticipant(CommunicationUserIdentifier(p), RoleType.ATTENDEE))
            self.rooms_client.add_participants(room_id, participants)
            print('\n(' + str(len(participants)) + ') new participants added to the room : ' + str(room_id))
        except Exception as ex:
            print('Error in adding participants to room.',ex)

    def remove_participants_from_room(self, room_id:str, participants_list:list):
        try:
            participants = []
            for p in participants_list:
                participants.append(CommunicationUserIdentifier(p))
            self.rooms_client.remove_participants(room_id=room_id, communication_identifiers=participants)
            print('\n(' + str(len(participants)) + ') participants removed from the room : ' + str(room_id))
        except Exception as ex:
            print(ex)

if __name__ == '__main__':
    print('==== Started : Rooms API Operations - Python Quickstart Sample ====')
    rooms = RoomsQuickstart()
    rooms.setup()
    rooms.create_room()
    rooms.update_room(room_id=rooms.roomsCollection[0])
    rooms.update_participants(room_id=rooms.roomsCollection[0], participants_list=[rooms.participant1, rooms.participant3])
    rooms.get_room_after_participants_update(room_id=rooms.roomsCollection[0])
    rooms.add_participants_to_room(room_id=rooms.roomsCollection[0], participants_list=[rooms.participant4, rooms.participant5, rooms.participant6])
    rooms.get_participants_in_room(room_id=rooms.roomsCollection[0])
    rooms.remove_participants_from_room(room_id=rooms.roomsCollection[0], participants_list=[rooms.participant4, rooms.participant5])
    rooms.get_participants_in_room(room_id=rooms.roomsCollection[0])
    rooms.teardown()

    print('==== Completed : Rooms API Operations - Python Quickstart Sample ====')