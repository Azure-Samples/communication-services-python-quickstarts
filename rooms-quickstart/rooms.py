from datetime import datetime, timezone, timedelta
from azure.core.exceptions import HttpResponseError
from azure.communication.rooms import (
    RoomsClient,
    RoomParticipant,
    ParticipantRole
)
from azure.communication.identity import (
    CommunicationIdentityClient,
    CommunicationUserIdentifier
)
class RoomsQuickstart(object):
    roomsCollection = []
    connection_string = '<connection_string>'
    identity_client = CommunicationIdentityClient.from_connection_string(connection_string)
    user1 = identity_client.create_user()
    user2 = identity_client.create_user()
    user3 = identity_client.create_user()
    user4 = identity_client.create_user()
    user5 = identity_client.create_user()

    def setup(self):
        self.rooms_client = RoomsClient.from_connection_string(self.connection_string)

    def teardown(self):
        self.delete_all_rooms()

    def create_room(self):
        try:
            valid_from = datetime.now(timezone.utc)
            valid_until = valid_from + timedelta(weeks=7)
            participants = []
            participant_1 = RoomParticipant(communication_identifier=self.user1, role=ParticipantRole.PRESENTER)
            participant_2 = RoomParticipant(communication_identifier=self.user2, role=ParticipantRole.CONSUMER)
            participant_3 = RoomParticipant(communication_identifier=self.user3, role=ParticipantRole.ATTENDEE)
            participants = [participant_1, participant_2, participant_3]
            created_room = self.rooms_client.create_room(
                valid_from=valid_from,
                valid_until=valid_until,
                participants=participants)
            print('\nRoom created.')
            self.print_room(created_room)
            self.roomsCollection.append(created_room.id)
        except Exception as ex:
            print('Room creation failed.', ex)

    def update_room(self, room_id:str):
        valid_from = datetime.now(timezone.utc)
        valid_until = valid_from + timedelta(weeks=1)
        try:
            updated_room = self.rooms_client.update_room(room_id=room_id, valid_from=valid_from, valid_until=valid_until)
            print('\nRoom updated with new valid_from and valid_until time.')
            self.print_room(updated_room)
        except HttpResponseError as ex:
            print(ex)

    def get_room(self, room_id:str):
        try:
            get_room = self.rooms_client.get_room(room_id=room_id)
            self.print_room(get_room)
        except HttpResponseError as ex:
            print(ex)

    def add_or_update_participants(self, room_id:str, participants_list:list):
        try:
            participants = []
            for p in participants_list:
                participants.append(RoomParticipant(communication_identifier=CommunicationUserIdentifier(p), role=ParticipantRole.ATTENDEE))
            self.rooms_client.add_or_update_participants(room_id=room_id, participants=participants)
            print('\nRoom participants added or updated.')
        except HttpResponseError as ex:
            print(ex)

    def list_all_rooms(self):
        rooms = self.rooms_client.list_rooms()
        print('\nList all active rooms')

        count = 0
        for room in rooms:
            if count == 1:
                break
            print("\nPrinting the first room in list"
              "\nRoom Id: " + room.id +
              "\nCreated date time: " + str(room.created_at) +
              "\nValid From: " + str(room.valid_from) + "\nValid Until: " + str(room.valid_until))
            count += 1

    def delete_all_rooms(self):
        for room_id in self.roomsCollection:
            print("\nDeleting room : ", room_id)
            self.rooms_client.delete_room(room_id)

    def print_room(self, room):
        print("\nRoom Id: " + room.id +
              "\nCreated date time: " + str(room.created_at) +
              "\nValid From: " + str(room.valid_from) + "\nValid Until: " + str(room.valid_until))

    def get_participants_in_room(self, room_id:str):
        participants = self.rooms_client.list_participants(room_id)
        print('\nParticipants in Room Id :', room_id)
        for p in participants:
            print(p.communication_identifier.properties['id'], p.role)

    def remove_participants_from_room(self, room_id:str, participants_list:list):
        try:
            participants = []
            for p in participants_list:
                participants.append(CommunicationUserIdentifier(p))
            self.rooms_client.remove_participants(room_id=room_id, participants=participants)
            print('\n(' + str(len(participants)) + ') participants removed from the room : ' + str(room_id))
        except Exception as ex:
            print(ex)

if __name__ == '__main__':
    print('==== Started : Rooms API Operations - Python Quickstart Sample ====')
    rooms = RoomsQuickstart()
    rooms.setup()
    rooms.create_room()
    rooms.update_room(room_id=rooms.roomsCollection[0])
    rooms.get_room(room_id=rooms.roomsCollection[0])
    rooms.add_or_update_participants(room_id=rooms.roomsCollection[0], participants_list=[rooms.user4.raw_id, rooms.user5.raw_id])
    rooms.list_all_rooms()
    rooms.get_participants_in_room(room_id=rooms.roomsCollection[0])
    rooms.remove_participants_from_room(room_id=rooms.roomsCollection[0], participants_list=[rooms.user4.raw_id, rooms.user5.raw_id])
    rooms.get_participants_in_room(room_id=rooms.roomsCollection[0])
    rooms.teardown()

    print('==== Completed : Rooms API Operations - Python Quickstart Sample ====')