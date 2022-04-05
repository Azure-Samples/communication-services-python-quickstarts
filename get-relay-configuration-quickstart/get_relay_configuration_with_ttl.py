# coding: utf-8

# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""
DESCRIPTION:
    This quickstart demonstrates how to get a relay configuration.
"""
import os
from azure.communication.networktraversal import CommunicationRelayClient
from azure.communication.identity import CommunicationIdentityClient
from aiortc import RTCPeerConnection, RTCConfiguration, RTCIceServer
from datetime import datetime, timezone, date

class CommunicationRelayClientSamples(object):

    connection_string = 'https://<RESOURCE_NAME>.communication.azure.com/;accesskey=<YOUR_ACCESS_KEY>'
    
    def get_relay_config(self):

        identity_client = CommunicationIdentityClient.from_connection_string(self.connection_string)
        relay_client = CommunicationRelayClient.from_connection_string(self.connection_string)
        
        print("Creating new user")
        user = identity_client.create_user()
        
        print("User created with id:" + user.properties.get('id'))

        print("Getting relay configuration")        
        request_time = datetime.now(timezone.utc)

        print("Requested time:")
        print(request_time)

        relay_configuration = relay_client.get_relay_configuration(ttl=60)

        print("Expires On")
        print(relay_configuration.expires_on)

        for iceServer in relay_configuration.ice_servers:
            print("Ice server:")
            print(iceServer)

        # You can now setup the RTCPeerConnection
        iceServersList = []

        # Create the list of RTCIceServers
        for iceServer in relay_configuration.ice_servers:
            iceServersList.append(RTCIceServer(username = iceServer.username, credential=iceServer.credential, urls = iceServer.urls))

        # Initialize the RTCConfiguration
        config = RTCConfiguration(iceServersList)

        # Initialize the RTCPeerConnection 
        pc = RTCPeerConnection(config)

if __name__ == '__main__':
    sample = CommunicationRelayClientSamples()
    sample.get_relay_config()