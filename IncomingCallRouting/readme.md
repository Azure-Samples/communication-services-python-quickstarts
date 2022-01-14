---
page_type: sample
languages:
  - python
products:
  - azure
  - azure-communication-services
---

# Incoming Call Routing Sample

This sample application shows how the Azure Communication Services Server, Calling package can be used to build IVR related solutions. This sample answer an incoming call from a phone number or a communication identifier and plays an audio message. If the caller presses 1 (tone1), the application will transfer the call. If the caller presses any other key then the application will ends the call after playing the audio message for a few times. The application is a console based application build using Python 3.9.

## Getting started

### Prerequisites

- Create an Azure account with an active subscription. For details, see [Create an account for free](https://azure.microsoft.com/free/)
- [Python](https://www.python.org/downloads/) 3.9 and above
- Create an Azure Communication Services resource. For details, see [Create an Azure Communication Resource](https://docs.microsoft.com/azure/communication-services/quickstarts/create-communication-resource). You'll need to record your resource **connection string** for this sample.
- Download and install [Ngrok](https://www.ngrok.com/download). As the sample is run locally, Ngrok will enable the receiving of all the events.
- Download and install [VSCode](https://code.visualstudio.com/)

> Note: the samples make use of the Microsoft Cognitive Services Speech SDK. By downloading the Microsoft Cognitive Services Speech SDK, you acknowledge its license, see [Speech SDK license agreement](https://aka.ms/csspeech/license201809).

### Configuring application

- Open the config.ini file to configure the following settings

  - Connection String: Azure Communication Service resource's connection string.
  - Base Url: base url of the endpoint
  - Audio File Uri: uri of the audio file
  - Target Participant: phone number/MRI of the participant
  - Bot Identity: identity of the bot

### Run the Application

- Add azure communication callingserver's wheel file path in requirement.txt
- Navigate to the directory containing the requirements.txt file and use the following commands for installing all the dependencies and for running the application respectively:
  - pip install -r requirements.txt
  - python program.py
