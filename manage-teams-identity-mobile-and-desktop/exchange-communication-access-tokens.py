import os
from azure.communication.identity import CommunicationIdentityClient, CommunicationUserIdentifier
from msal.application import PublicClientApplication

try:
   print("Azure Communication Services - Access Tokens Quickstart")
   # Quickstart code goes here
   
   # This code demonstrates how to fetch your Azure AD client ID and tenant ID
   # from an environment variable.
   client_id = os.environ["AAD_CLIENT_ID"]
   tenant_id = os.environ["AAD_TENANT_ID"]
   authority = "https://login.microsoftonline.com/%s" % tenant_id
   
   # Create an instance of PublicClientApplication
   app = PublicClientApplication(client_id, authority=authority)

   scopes = [ 
   "https://auth.msft.communication.azure.com/Teams.ManageCalls",
   "https://auth.msft.communication.azure.com/Teams.ManageChats"
   ]
   
   # Retrieve the AAD token and object ID of a Teams user
   result = app.acquire_token_interactive(scopes)
   aad_token =  result["access_token"]
   user_object_id = result["id_token_claims"]["oid"]
   print(f"Teams token:{aad_token}")
   
   # This code demonstrates how to fetch your connection string
   # from an environment variable.
   connection_string = os.environ["COMMUNICATION_SERVICES_CONNECTION_STRING"]

   # Instantiate the identity client
   client = CommunicationIdentityClient.from_connection_string(connection_string)
   
   # Exchange the Azure AD access token of the Teams User for a Communication Identity access token
   token_result = client.get_token_for_teams_user(aad_token, client_id, user_object_id)
   print("Token: " + token_result.token)
   
except Exception as ex:
   print(f"Exception: {ex}")