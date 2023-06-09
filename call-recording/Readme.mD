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
It harnesses the power of Azure Communication Services to establish connections and enable communication features within the application. A separate branch with end to end implementation is available. It's a public preview branch and uses beta SDKs that are not meant for production use. Please use the main branch sample for any production scenarios.

## Getting started

### Prerequisites

- Create an Azure account with an active subscription. For details, see [Create an account for free](https://azure.microsoft.com/free/)
- Create an Azure Communication Services resource. For details, see [Create an Azure Communication Resource](https://docs.microsoft.com/azure/communication-services/quickstarts/create-communication-resource). You'll need to record your resource **connection string** for this sample.
- Get a phone number for your new Azure Communication Services resource. For details, see [Get a phone number](https://docs.microsoft.com/azure/communication-services/quickstarts/telephony-sms/get-phone-number?pivots=platform-azp)
- Download and install [VS Code](https://code.visualstudio.com/download) or  [Visual Studio (2022 v17.4.0 and above)](https://visualstudio.microsoft.com/vs/)
-[Python311](https://www.python.org/downloads/) (Make sure to install version that corresponds with your visual studio instance, 32 vs 64 bit)
- Download and install [Ngrok](https://www.ngrok.com/download). As the sample is run locally, Ngrok will enable the receiving of all the events.
- Generate Ngrok Url by using below steps.
    - Open command prompt or powershell window.
    - Navigate to the directory, where Ngrok.exe file is located. Then, run:
    - ngrok http {portNumber}(For e.g. ngrok http 58963)
    - Get Ngrok Url generated. Ngrok Url will be in the form of e.g. "https://95b6-43-230-212-228.ngrok-free.app"
- Create a webhook and subscribe to the recording events. For details, see [Create webhook](https://docs.microsoft.com/azure/communication-services/quickstarts/voice-video-calling/download-recording-file-sample)

## Clone the code local and update configuration

1. Open an instance of PowerShell, Windows Terminal, Command Prompt or equivalent and navigate to the directory that you'd like to clone the sample to.
2. Run `git clone https://github.com/moirf/communication-services-python-quickstarts.git`
3. Once you get the code on local machine, navigate to **call-recording/config.ini** file found under the call-recording folder.
4. Update the values for below.

	| Key | Value | Description |
	| -------- | -------- | -------- |
	| `ACSResourceConnectionString`    | \<ACS Connection String>   | Input your ACS connection string in the variable   |
	| `ACSAcquiredPhoneNumber`    | \<ACS Acquired Number>   | Phone number associated with the Azure Communication Service resource   |
	| `BaseUri`    | \<ngrok url>   | Base url of the app, don't add `/` at end. generate ngrok url as mentioned above.   |


## Code structure

- *./call-recording/Controller* : Server app core logic for calling the recording APIs using Azure Communication Services callautomation SDK
- *./call-recording/App.py* : Entry point for the server app program logic
- *./call-recording/requirement.txt* : Contains dependencies for running and deploying the application

### Setup the Python environment

Create and activate python virtual environment and install required packages using following command in `call-recording` folder.
```
pip install -r requirements.txt
```

## Run app locally

1. Navigate to `call-recording` folder and run `App.py` in debug mode or use command `python ./App.py` to run it from PowerShell, Command Prompt or Unix Terminal
2. Import `call-recording\data\Recordings API.postman_collection.json` file into postman
3. update `Host_Name` in postman API's before making a call.

### Step by step guid for testing recording APIs via swagger.
1. Step 1. Start a call invoke OutboundCall.
	- Try it out `GET OutboundCall`, provide the Target PSTN phone number under query params to get the call.
	- `Send`, accept the call on Target PSTN Phone number, Keep call running.
2. Step 2. Start Recording.
	-	Try it out `GET StartRecording`, provide the serverCallId value, optional if recording the same call started in *step1*.
	- 	`Send`, recording would be started.
3. Step 3. (Optional) Execute `GET PauseRecording` and then `GET ResumeRecording`, passing recordingId is optional.
4. Step 4. Execute `GET StopReocording` to stop the recording, passing recordingId is optional.
5. Step 5. Execute `GET DownloadRecording` for downloading the recording from server, only last recorded file will be downloaded.
6. Step 6. Execute `DELETE DeleteRecording` for delete the recording at server.
