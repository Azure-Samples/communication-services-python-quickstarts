---
page_type: sample
languages:
- Python
products:
- azure
- azure-communication-services
---


# Manage Phone Numbers

For full instructions on how to build this code sample from scratch, look at [Quickstart: Send an SMS message](https://docs.microsoft.com/azure/communication-services/quickstarts/telephony-sms/send?pivots=programming-language-python)

## Prerequisites

- An Azure account with an active subscription. [Create an account for free](https://azure.microsoft.com/free/?WT.mc_id=A261C142F). 
- [Python](https://www.python.org/downloads/) 3.7+.
- An active Communication Services resource and connection string. [Create a Communication Services resource](https://docs.microsoft.com/azure/communication-services/quickstarts/create-communication-resource).
- An SMS enabled telephone number. [Get a phone number](https://docs.microsoft.com/azure/communication-services/quickstarts/telephony-sms/get-phone-number?pivots=programming-language-python).

## Code Structure

- **./send-sms-quickstart/send-sms.py:** contains code for sending message.

## Install the packages

- pip install azure-communication-sms

## Before running sample code

1. Open an instance of PowerShell, Windows Terminal, Command Prompt or equivalent and navigate to the directory that you'd like to clone the sample to.
2. `git clone https://github.com/Azure-Samples/communication-services-python-quickstarts.git`.
3. With the Communication Services procured in pre-requisites, add connection string to **send-sms.py** file at line no:8 ```sms_client = SmsClient.from_connection_string("<connection_string>")```.
4. With the SMS enabled telephone number procured in pre-requisites, add it to the **send-sms.py** file. Assign your ACS telephone number and sender numbers at line no 22 & 23.
   

## Run Locally

From a console prompt, navigate to the directory containing the send-sms.py file, then execute the following command to run the app.

python ./send-sms.py

