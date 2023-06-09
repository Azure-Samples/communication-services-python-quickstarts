---
page_type: sample
languages:
- python
products:
- azure
- azure-communication-CallAutomation
---

#  Sample
This is a sample application to showcase how the Call Automation SDK can be used to add recording features to any application.
The application is a console based application build using Python 3.9 and above.

## Getting started

### Prerequisites

- Create an Azure account with an active subscription. For details, see [Create an account for free](https://azure.microsoft.com/free/)
- [Python](https://www.python.org/downloads/) 3.9 and above
- Create an Azure Communication Services resource. For details, see [Create an Azure Communication Resource](https://docs.microsoft.com/azure/communication-services/quickstarts/create-communication-resource). You'll need to record your resource **connection string** for this sample.
- Get a phone number for your new Azure Communication Services resource. For details, see [Get a phone number](https://docs.microsoft.com/azure/communication-services/quickstarts/telephony-sms/get-phone-number?pivots=platform-azp)
- Download and install [VS Code](https://code.visualstudio.com/download) or  [Visual Studio (2022 v17.4.0 and above)](https://visualstudio.microsoft.com/vs/) 
-[Python311](https://www.python.org/downloads/) (Make sure to install version that corresponds with your visual studio instance, 32 vs 64 bit)
- Download and install [Ngrok](https://www.ngrok.com/download). As the sample is run locally, Ngrok will enable the receiving of all the events.
- Generate Ngrok Url by using below steps.
    - Open command prompt or powershell window on the machine using to run the sample.
    - Navigate to directory path where Ngrok.exe file is located. Then, run:
    - ngrok http {portNumber}(For e.g. ngrok http 8080)
    - Get Ngrok Url generated. Ngrok Url will be in the form of e.g. "https://95b6-43-230-212-228.ngrok-free.app"
- Create a webhook and subscribe to the recording events. For details, see [Create webhook](https://docs.microsoft.com/azure/communication-services/quickstarts/voice-video-calling/download-recording-file-sample)
- [Install Docker](https://docs.docker.com/desktop/windows/install/)

## Code structure

- ./call-recording/Controller : Server app core logic for calling the recording APIs using Azure Communication Services server calling SDK
- ./call-recording/App.py : Entry point for the server app program logic
- ./call-recording/requirement.txt : Contains dependencies for running and deploying the application

### Before running the sample for the first time

 -Open an instance of PowerShell, Windows Terminal, Command Prompt or equivalent and navigate to  the    directory that you would like to clone the sample to.
 -git clone "https://github.com/moirf/communication-services-python-quickstarts".
 Navigate to call-recording folder.
 3. Once you get the config keys add the keys to the **call-recording/config.ini**  file found under the Main folder.
	- Input your ACS connection string in the variable `Connectionstring`
	- Input your ACS accquired phone number in the variable `ACSAcquiredPhoneNumber`
	- Input recording callback url for start recording api in the variable `CallbackUri`
	

### Configuring application

- Open the config.ini file to configure the following settings
- Connection String: Azure Communication Service resource's connection string.
- Source Phone: Phone number associated with the Azure Communication Service resource.
- target Identity: Multiple sets of outbound target and Transfer target. These sets are seperated by a semi-colon, and outbound target and Transfer target in a each set are seperated by a coma.
-App_base_uri: Base url of the app. (For local development replace the Ngrok url.For e.g. "https://95b6-43-230-212-228.ngrok-free.app")  

### Run the Application

- Add azure communication callautomation's wheel file path in requirement.txt
- Navigate to the directory containing the requirements.txt file and use the following commands for installing all the dependencies and for running the application respectively:
     - pip install -r requirements.txt
     - python program.py
