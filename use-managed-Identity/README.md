---
page_type: sample
languages:
- Python
products:
- azure
- azure-communication-services
- azure-communication-sms
---


# Use managed identities

For full instructions on how to build this code sample from scratch, look at [Quickstart: Use managed identities](https://docs.microsoft.com/azure/communication-services/quickstarts/managed-identity?pivots=programming-language-python)

## Prerequisites

- An Azure account with an active subscription. [Create an account for free](https://azure.microsoft.com/free/?WT.mc_id=A261C142F). 
- [Python](https://www.python.org/downloads/) 3.7 or above.
- A deployed Communication Services resource and connection string. [Create a Communication Services resource](https://docs.microsoft.com/azure/communication-services/quickstarts/create-communication-resource).
- To send an SMS you will need a [Phone Number](https://docs.microsoft.com/azure/communication-services/quickstarts/telephony-sms/get-phone-number?pivots=programming-language-python).
- A setup managed identity for a development environment, see [Authorize access with managed identity](https://docs.microsoft.com/azure/communication-services/quickstarts/managed-identity-from-cli).
## Code Structure

- **./use-managed-Identity/managed-identity.py:** contains code to use managed identities.

## Install the packages

- pip install azure-identity
- pip install azure-communication-identity
- pip install azure-communication-sms

## Before running sample code

1. Open an instance of PowerShell, Windows Terminal, Command Prompt or equivalent and navigate to the directory that you'd like to clone the sample to.
2. `git clone https://github.com/Azure-Samples/communication-services-python-quickstarts.git`
3. With the Communication Services procured in pre-requisites, add endpoint to the **managed-identity.py** file at line no 29: ```endpoint = "https://<RESOURCE_NAME>.communication.azure.com/"```.
4.  With the SMS enabled telephone number procured in pre-requisites, add it to the **managed-identity.py** file. Assign your ACS telephone number and sender number at line 36: ```sms_result = send_sms(endpoint, "<FROM_NUMBER>", "<TO_NUMBER>", "Hello from Managed Identities");```

## Run Locally

From a console prompt, navigate to the directory containing the managed-identity.py file, then execute the following command to run the app.

python ./managed-identity.py

