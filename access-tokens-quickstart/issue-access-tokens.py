import os
from azure.communication.identity import CommunicationIdentityClient, CommunicationUserIdentifier

try:
	print("Azure Communication Services - Access Tokens Quickstart")
   
	# This code demonstrates how to fetch your connection string from an environment variable.
	connection_string = os.environ["COMMUNICATION_SERVICES_CONNECTION_STRING"]

	# Instantiate the identity client
	client = CommunicationIdentityClient.from_connection_string(connection_string)
	
	# Create an identity
	identity = client.create_user()
	print("\nCreated an identity with ID: " + identity.identifier)

	#Store the identity to issue access tokens later
	existingIdentity = identity	

	# Issue an access token with the "voip" scope for an identity
	token_result = client.get_token(identity, ["voip"])
	expires_on = token_result.expires_on.strftime("%d/%m/%y %I:%M %S %p")
	print("\nIssued an access token with 'voip' scope that expires at " + expires_on + ":")
	print(token_result.token)
	
	# Create an identity and issue an access token within the same request
	identity_token_result = client.create_user_and_token(["voip"])
	identity = identity_token_result[0].identifier
	token = identity_token_result[1].token
	expires_on = identity_token_result[1].expires_on.strftime("%d/%m/%y %I:%M %S %p")
	print("\nCreated an identity with ID: " + identity)
	print("\nIssued an access token with 'voip' scope that expires at " + expires_on + ":")
	print(token)

	# Refresh access tokens - existingIdentity represents identity of Azure Communication Services stored during identity creation
	identity = CommunicationUserIdentifier(existingIdentity.identifier)	
	token_result = client.get_token( identity, ["voip"])

	# Revoke access tokens
	client.revoke_tokens(identity)
	print("\nSuccessfully revoked all access tokens for identity with ID: " + identity.identifier)

	# Delete an identity
	client.delete_user(identity)
	print("\nDeleted the identity with ID: " + identity.identifier)

except Exception as ex:
   print("Exception:")
   print(ex)