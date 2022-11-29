---
page_type: sample
languages:
- Python
products:
- azure
- azure-communication-chat
- azure-communication-identity
---


# Add Chat to your App

For full instructions on how to build this code sample from scratch, look at [Quickstart: Add Chat to your App](https://docs.microsoft.com/azure/communication-services/quickstarts/chat/get-started?pivots=programming-language-python)

## Prerequisites

- An Azure account with an active subscription. [Create an account for free](https://azure.microsoft.com/free/?WT.mc_id=A261C142F). 
- Install [Python](https://www.python.org/downloads/) 3.7 or above.
- Create an Azure Communication Services resource. For details, see [Quickstart: Create and manage Communication Services resources](https://docs.microsoft.com/azure/communication-services/quickstarts/create-communication-resource). You'll need to record your resource endpoint for this quickstart.
- A [user access token](https://docs.microsoft.com/azure/communication-services/quickstarts/access-tokens?pivots=programming-language-python). Be sure to set the scope to **chat**, and note the **token** string as well as the **userId** string.

## Code Structure

- **./add-chat/start-chat.py:** contains code for chat.

## Install the packages

pip install azure-communication-chat

pip install azure-communication-identity

## Before running sample code

1. Open an instance of PowerShell, Windows Terminal, Command Prompt or equivalent and navigate to the directory that you'd like to clone the sample to.
2. `git clone https://github.com/Azure-Samples/communication-services-python-quickstarts.git`
3. With the Communication Services procured in pre-requisites, add endpoint to **start-chat.py** file at line no:11 ```endpoint = "https://<RESOURCE_NAME>.communication.azure.com"```.
4. With the access token procured in pre-requisites, add it to the **start-chat.py** file. Assign token at line no:12 ```chat_client = ChatClient(endpoint, CommunicationTokenCredential("<Access Token>"))```.
5. With the Communication Services procured in pre-requisites, add connection string to **start-chat.py** file at line no:58 ```identity_client = CommunicationIdentityClient.from_connection_string('<connection_string>')```.
   

## Run Locally

From a console prompt, navigate to the directory containing the start-chat.py file, then execute the following command to run the app.

python ./start-chat.py

