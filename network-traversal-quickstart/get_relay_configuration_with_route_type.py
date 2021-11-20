# coding: utf-8

# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""
DESCRIPTION:
    These samples demonstrates how to get a relay configuration.
"""
import os
from azure.communication.networktraversal import RouteType
from azure.communication.networktraversal._shared.utils import parse_connection_str

class CommunicationRelayClientSamples(object):

    def __init__(self):
        self.connection_string = os.getenv('COMMUNICATION_SAMPLES_CONNECTION_STRING')
        self.client_id = os.getenv('AZURE_CLIENT_ID')
        self.client_secret = os.getenv('AZURE_CLIENT_SECRET')
        self.tenant_id = os.getenv('AZURE_TENANT_ID')

    def get_relay_config(self):
        from azure.communication.networktraversal import (
            CommunicationRelayClient
        )

        if self.client_id is not None and self.client_secret is not None and self.tenant_id is not None:
            from azure.identity import DefaultAzureCredential
            endpoint, _ = parse_connection_str(self.connection_string)
            relay_client = CommunicationRelayClient(endpoint, DefaultAzureCredential())
        else:
            relay_client = CommunicationRelayClient.from_connection_string(self.connection_string)

        print("Getting relay configuration")
        relay_configuration = relay_client.get_relay_configuration(route_type = RouteType.ANY)

        for iceServer in relay_configuration.ice_servers:
            print("Ice server:")
            print(iceServer)

if __name__ == '__main__':
    sample = CommunicationRelayClientSamples()
    sample.get_relay_config()