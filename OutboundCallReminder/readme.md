---
page_type: sample
languages:
- python
products:
- azure
- azure-communication-services
---

# Outbound Reminder Call Sample

This sample application shows how the Azure Communication Services Server, Calling package can be used to build IVR related solutions. This sample makes an outbound call to a phone number or a communication identifier and plays an audio message. If the callee presses 1 (tone1), to reschedule an appointment, then the application invites a new participant and then leaves the call. If the callee presses any other key then the application ends the call. This sample application is also capable of making multiple concurrent outbound calls.
The application is a console based application build using Python 3.9.

## Getting started

### Prerequisites

- Create an Azure account with an active subscription. For details, see [Create an account for free](https://azure.microsoft.com/free/)
- [Python](https://www.python.org/downloads/) 3.9 and above
- Create an Azure Communication Services resource. For details, see [Create an Azure Communication Resource](https://docs.microsoft.com/azure/communication-services/quickstarts/create-communication-resource). You'll need to record your resource **connection string** for this sample.
- Get a phone number for your new Azure Communication Services resource. For details, see [Get a phone number](https://docs.microsoft.com/azure/communication-services/quickstarts/telephony-sms/get-phone-number?pivots=platform-azp)
- Download and install [Ngrok](https://www.ngrok.com/download). As the sample is run locally, Ngrok will enable the receiving of all the events.
- Download and install  [Visual C++](https://support.microsoft.com/en-us/topic/the-latest-supported-visual-c-downloads-2647da03-1eea-4433-9aff-95f26a218cc0)
- (Optional) Create Azure Speech resource for generating custom message to be played by application. Follow [here](https://docs.microsoft.com/azure/cognitive-services/speech-service/overview#try-the-speech-service-for-free) to create the resource.

> Note: the samples make use of the Microsoft Cognitive Services Speech SDK. By downloading the Microsoft Cognitive Services Speech SDK, you acknowledge its license, see [Speech SDK license agreement](https://aka.ms/csspeech/license201809).

### Configuring application

- Open the config.ini file to configure the following settings

	- Connection String: Azure Communication Service resource's connection string.
	- Source Phone: Phone number associated with the Azure Communication Service resource.
	- DestinationIdentities: Multiple sets of outbound target and Transfer target. These sets are seperated by a semi-colon, and outbound target and Transfer target in a each set are seperated by a coma.

    	Format: "OutboundTarget1(PhoneNumber),TransferTarget1(PhoneNumber/MRI);OutboundTarget2(PhoneNumber),TransferTarget2(PhoneNumber/MRI);OutboundTarget3(PhoneNumber),TransferTarget3(PhoneNumber/MRI)".

	  	For e.g. "+1425XXXAAAA,8:acs:ab12b0ea-85ea-4f83-b0b6-84d90209c7c4_00000009-bce0-da09-54b7-xxxxxxxxxxxx;+1425XXXBBBB,+1425XXXCCCC"

	- NgrokExePath: Folder path where ngrok.exe is insalled/saved.
	- SecretPlaceholder: Secret/Password that would be part of callback and will be use to validate incoming requests.
	- CognitiveServiceKey: (Optional) Cognitive service key used for generating custom message
	- CognitiveServiceRegion: (Optional) Region associated with cognitive service
	- CustomMessage: (Optional) Text for the custom message to be converted to speech.

### Run the Application

- Add azure communication callingserver's wheel file path in requirement.txt
- Navigate to the directory containing the requirements.txt file and use the following commands for installing all the dependencies and for running the application respectively:
	- pip install -r requirements.txt
	- python program.py
