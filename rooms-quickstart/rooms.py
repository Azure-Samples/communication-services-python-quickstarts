import sys

from datetime import datetime
from dateutil.relativedelta import relativedelta
from azure.core.exceptions import HttpResponseError
from azure.communication.rooms import (
    RoomsClient,
    RoomParticipant
)
from azure.communication.identity import CommunicationUserIdentifier

class RoomsQuickstart(object):
    roomsCollection = []
    connection_string = '<connection_string>'
    participant1 = '<communication_identifiers>'
    participant2 = '<communication_identifiers>'
    participant3 = '<communication_identifiers>'
    participant4 = '<communication_identifiers>'

    def setUp(self):
        self.rooms_client = RoomsClient.from_connection_string(self.connection_string)
        
    def tearDown(self):
        self.delete_all_rooms()
    
    def create_room(self):
        try:
            valid_from = datetime.now()
            valid_until = valid_from + relativedelta(months=+1,days=+20)

            participants = []
            participants.append(RoomParticipant(CommunicationUserIdentifier(self.participant1)))

            create_room_response = self.rooms_client.create_room(valid_from=valid_from, valid_until=valid_until, participants=participants)
            print('\nRoom created...')
            self.print_room(create_room_response)

            self.roomsCollection.append(create_room_response.id)

        except Exception as ex:
            print(ex)

    def update_room(self, room_id:str):
        valid_from = datetime.now()
        valid_until = valid_from + relativedelta(months=+1,days=+20)

        try:
            update_room_response = self.rooms_client.update_room(room_id=room_id, valid_from=valid_from, valid_until=valid_until)
            print('\nRoom updated...')
            self.print_room(response=update_room_response)
        except HttpResponseError as ex:
            print(ex)

    def delete_all_rooms(self):
        for room in self.roomsCollection:
            print("\nDeleting room : ", room)
            self.rooms_client.delete_room(room_id=room)
    
    def print_room(self, response):
        print("room Id: " + response.id  + "\n" + 
        "created date time: " + str(response.created_date_time) + "\n"  + 
        "valid_from: " + str(response.valid_from) + "\n" + "valid_until: ", str(response.valid_until))

    def get_participants_in_room(self, room_id:str):
        room = self.rooms_client.get_room(room_id=room_id)
        participants = room.participants
        participants_list = list(participants)
        print('\nCurrent room participants : \n' + 'S.no. - '+ 'User Id')
        for p in participants_list:
            print(str(participants_list.index(p)) + ' -     ' + str(p.communication_identifier.properties['id']) )

    def add_participant_to_room(self, room_id:str, participants:list):
        try:
            users = []
            for p in participants:
                users.insert(participants.index(p), RoomParticipant(CommunicationUserIdentifier(p)))
            self.rooms_client.add_participants(room_id=room_id, participants=users)
            print('\nAdded ' + str(len(participants)) + ' new participants to the Room : ' + str(room_id))
        except Exception as ex:
            print(ex)

    def remove_participant_from_room(self, room_id:str, participants:list):
        try:
            users = []
            for p in participants:
                users.insert(participants.index(p), CommunicationUserIdentifier(p))
            self.rooms_client.remove_participants(room_id=room_id, communication_identifiers=users)
            print('n\Removed ' + str(len(participants)) + ' participants from the Room : ' + str(room_id))
        except Exception as ex:
            print(ex)

if __name__ == '__main__':
    rooms = RoomsQuickstart()
    rooms.setUp()
    print('-----------------Starting room operations of create --> update --> add --> get --> delete-----------------------')
    
    rooms.create_room()
    rooms.update_room(room_id=rooms.roomsCollection[0])
    rooms.add_participant_to_room(rooms.roomsCollection[0], [rooms.participant2, rooms.participant3, rooms.participant4]  )
    rooms.get_participants_in_room(rooms.roomsCollection[0])
    rooms.remove_participant_from_room(rooms.roomsCollection[0], [rooms.participant3, rooms.participant4])
    rooms.get_participants_in_room(rooms.roomsCollection[0])

    rooms.tearDown()

    print('-----------------Completed room operations of create --> update --> add --> get --> delete-----------------------')