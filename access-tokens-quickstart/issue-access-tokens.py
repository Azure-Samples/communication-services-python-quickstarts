import os
from datetime import timedelta
from azure.communication.identity import CommunicationIdentityClient, CommunicationUserIdentifier

try:
	print("Azure Communication Services - Access Tokens Quickstart")
   
	# This code demonstrates how to fetch your connection string from an environment variable.
	connection_string = os.environ["COMMUNICATION_SERVICES_CONNECTION_STRING"]

	# Instantiate the identity client
	client = CommunicationIdentityClient.from_connection_string(connection_string)
	
	# Create an identity
	identity = client.create_user()
	print("\nCreated an identity with ID: " + identity.properties['id'])

	#Store the identity to issue access tokens later
	existingIdentity = identity	

	# Issue an access token with validity of 24 hours and the "voip" scope for an identity
	token_result = client.get_token(identity, ["voip"])
	print("\nIssued an access token with 'voip' scope that expires at " + token_result.expires_on + ":")
	print(token_result.token)
 
	# Issue an access token with validity of an hour and the "voip" scope for an identity
	token_expires_in = timedelta(hours=1)
	token_result = client.get_token(identity, ["voip"], token_expires_in=token_expires_in)
	print("\nIssued an access token with 'voip' scope and custom expiration that expires at " + token_result.expires_on + ":")
	print(token_result.token)
	
	# Create an identity and issue an access token with validity of 24 hours within the same request
	identity_token_result = client.create_user_and_token(["voip"])
	# Get the token details from the response
	identity = identity_token_result[0].properties['id']
	token = identity_token_result[1].token
	expires_on = identity_token_result[1].expires_on
	print("\nCreated an identity with ID: " + identity)
	print("\nIssued an access token with 'voip' scope that expires at " + expires_on + ":")
	print(token)
 
	# Create an identity and issue an access token with validity of an hour within the same request
	identity_token_result = client.create_user_and_token(["voip"], token_expires_in=token_expires_in)
	# Get the token details from the response
	identity = identity_token_result[0].properties['id']
	token = identity_token_result[1].token
	expires_on = identity_token_result[1].expires_on
	print("\nCreated an identity with ID: " + identity)
	print("\n**ßIssued an access token with 'voip' scope and custom expiration that expires at " + expires_on + ":")
	print(token)
 	
	# Refresh access tokens - existingIdentity represents identity of Azure Communication Services stored during identity creation
	identity = CommunicationUserIdentifier(existingIdentity.properties['id'])
	token_result = client.get_token( identity, ["voip"])

	# Revoke access tokens
	client.revoke_tokens(identity)
	print("\nSuccessfully revoked all access tokens for identity with ID: " + identity.properties['id'])

	# Delete an identity
	client.delete_user(identity)
	print("\nDeleted the identity with ID: " + identity.properties['id'])

except Exception as ex:
   print("Exception:")
   print(ex)