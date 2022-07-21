from datetime import datetime, timezone
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
    participant1 = '<communication_identifier>'
    participant2 = '<communication_identifier>'
    participant3 = '<communication_identifier>'
    participant4 = '<communication_identifier>'

    def setUp(self):
        self.rooms_client = RoomsClient.from_connection_string(self.connection_string)
        
    def tearDown(self):
        self.delete_all_rooms()
    
    def create_room(self):
        try:
            valid_from = datetime.now(timezone.utc)
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
        valid_from = datetime.now(timezone.utc)
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
        "valid_from: " + str(response.valid_from) + "\n" + "valid_until: ", str(response.valid_until) + "\n" +
        "Participants : \n" )
        for i in range(len(response.participants)):
            print(str(i+1) + ' -    ' + response.participants[i].communication_identifier.properties['id'])

    def get_participants_in_room(self, room_id:str):
        room = self.rooms_client.get_room(room_id=room_id)
        participants = room.participants
        print('\nCurrent room participants : \n' + 'S.no.  '+ 'User Id')
        for i in range(len(participants)):
            print(str(i+1) + ' -    ' + participants[i].communication_identifier.properties['id'])

    def add_participant_to_room(self, room_id:str, participants:list):
        try:
            participants_to_add = []
            for i in range(len(participants)):
                participants_to_add.insert(i, RoomParticipant(CommunicationUserIdentifier(participants[i])))

            self.rooms_client.add_participants(room_id=room_id, participants=participants_to_add)
            print('\nAdded ' + str(len(participants)) + ' new participants to the Room : ' + str(room_id))
        except Exception as ex:
            print(ex)

    def remove_participant_from_room(self, room_id:str, participants:list):
        try:
            participants_to_remove = []
            for i in range(len(participants)):
                participants_to_remove.insert(i, CommunicationUserIdentifier(participants[i]))
            self.rooms_client.remove_participants(room_id=room_id, communication_identifiers=participants_to_remove)
            print('\nRemoved ' + str(len(participants)) + ' participants from the Room : ' + str(room_id))
        except Exception as ex:
            print(ex)

if __name__ == '__main__':
    print('-----------------Starting room operations of create --> update --> add --> get --> delete-----------------------')

    rooms = RoomsQuickstart()
    rooms.setUp()
    rooms.create_room()
    rooms.update_room(room_id=rooms.roomsCollection[0])
    rooms.add_participant_to_room(rooms.roomsCollection[0], [rooms.participant2, rooms.participant3, rooms.participant4]  )
    rooms.get_participants_in_room(rooms.roomsCollection[0])
    rooms.remove_participant_from_room(rooms.roomsCollection[0], [rooms.participant3, rooms.participant4])
    rooms.get_participants_in_room(rooms.roomsCollection[0])
    rooms.tearDown()

    print('-----------------Completed room operations of create --> update --> add --> get --> delete-----------------------')