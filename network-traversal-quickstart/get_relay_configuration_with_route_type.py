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
from azure.communication.networktraversal import RouteType

class CommunicationRelayClientSamples(object):

    connection_string = 'https://<RESOURCE_NAME>.communication.azure.com/;accesskey=<YOUR_ACCESS_KEY>'

    def get_relay_config(self):
        from azure.communication.networktraversal import (
            CommunicationRelayClient
        )

        relay_client = CommunicationRelayClient.from_connection_string(self.connection_string)

        print("Getting relay configuration")
        relay_configuration = relay_client.get_relay_configuration(route_type = RouteType.NEAREST)

        for iceServer in relay_configuration.ice_servers:
            print("Ice server:")
            print(iceServer)

if __name__ == '__main__':
    sample = CommunicationRelayClientSamples()
    sample.get_relay_config()