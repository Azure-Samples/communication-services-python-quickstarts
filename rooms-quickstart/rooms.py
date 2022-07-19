import sys

from datetime import datetime
from dateutil.relativedelta import relativedelta
from azure.core.exceptions import HttpResponseError
from azure.communication.rooms import (
    RoomsClient,
    RoomParticipant
)

sys.path.append("..")

class RoomsQuickstart(object):
    rooms = [];
    
    def setUp(self):
        self.rooms_client = RoomsClient.from_connection_string('<connection_string>')
  
    def tearDown(self):
        self.delete_all_rooms()
    
    def create_room(self):
        try:
            # set room attributes
            valid_from = datetime.now()
            valid_until = valid_from + relativedelta(months=+4)
            participants = {}

            participants['<acs_resource_user_id>'] = RoomParticipant()

            create_room_response = self.rooms_client.create_room(valid_from=valid_from, valid_until=valid_until, participants=participants)
            self.print_room(response=create_room_response)

            # all created room to a list
            self.rooms.append(create_room_response.id)

        except Exception as ex:
            print(ex)


    def update_room(self, room_id:str):
        valid_from =  datetime.now()
        valid_until = valid_from + relativedelta(months=+1,days=+20)

        try:
            update_room_response = self.rooms_client.update_room(room_id=room_id, valid_from=valid_from, valid_until=valid_until)
            self.print_room(response=update_room_response)
        except HttpResponseError as ex:
            print(ex)

    def delete_all_rooms(self):
        for room in self.rooms:
            print("deleting room : ", room)
            self.rooms_client.delete_room(room_id=room)
    
    def print_room(self, response):
        print("room Id: " + response.id  + "\n" + "created date time: " + str(response.created_date_time) + "\n"  + "valid_from: " + str(response.valid_from) + "\n" + "valid_until: ", str(response.valid_until))

    def get_participants_in_room(self, room_id:str):
        room = self.rooms_client.get_room(room_id=room_id)
        participants = room.participants
        for p in participants:
            print(p + '\n')
        print('count of particiapants in room : ' + room_id + ' = ' + str(len(participants)))
        

    def add_participant_to_room(self, room_id:str, participant_id:str):
        try:
            participant = {participant_id: {}}
            self.rooms_client.add_participants(room_id=room_id, participants=participant)
        except Exception as ex:
            print(ex)

if __name__ == '__main__':
    room_quick_start = RoomsQuickstart()
    room_quick_start.setUp()
    print('-----------------creating a room-----------------------')
    room_quick_start.create_room()

    print('------------------get participants in room----------------------')
    room_quick_start.get_participants_in_room(room_quick_start.rooms[0])

    print('-----------------update room-----------------------')
    room_quick_start.update_room(room_id=room_quick_start.rooms[0])

    print('-------------------------adding a participant to room-----------------------')
    room_quick_start.add_participant_to_room(room_quick_start.rooms[0], '<acs_resource_user_id>' )
    
    print('-------------------get updated participants in room---------------------')
    room_quick_start.get_participants_in_room(room_quick_start.rooms[0])

    print('-------------------deleting the room---------------------')
    room_quick_start.tearDown()