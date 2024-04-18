---
page_type: sample
languages:
- Python

Products:
- azure
- azure-communication-rooms
---


# Manage Rooms

For full instructions on how to build this code sample from scratch, look at [Quickstart: Create a room]

## Prerequisites

- An Azure account with an active subscription. [Create an account for free](https://azure.microsoft.com/free/?WT.mc_id=A261C142F).
- Install [Python](https://www.python.org/downloads/) 3.7 or above.
- Create an Azure Communication Services resource. For details, see [Quickstart: Create and manage Communication Services resources](https://docs.microsoft.com/azure/communication-services/quickstarts/create-communication-resource). You'll need to record your resource endpoint for this quickstart.
- Create a  [user access token](https://docs.microsoft.com/azure/communication-services/quickstarts/access-tokens?pivots=programming-language-python). Be sure to set the scope to **voip**, and note the **token** string as well as the **userId** string.

## Code Structure

- **./rooms-python-quickstart/rooms.py:** contains code for managing rooms.

## Install the packages

From a console prompt, navigate to the directory containing the rooms.py file, then execute the following command:

- pip install azure-communication-rooms==1.1.0
- pip install azure-communication-identity

## Before running sample code

1. Open an instance of PowerShell/Windows Terminal/Command Prompt or equivalent and navigate to the directory that you'd like to clone the sample to.
2. `git clone https://github.com/Azure-Samples/communication-services-python-quickstarts.git`
3. With the Communication Services procured in pre-requisites, add connection string in **rooms.py** file at line 14 ```connection_string = '<connection_string>'```.

## Run Locally

From a console prompt, navigate to the directory containing the rooms.py file, then execute the following command to run the app.

python ./rooms.py
