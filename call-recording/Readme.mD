---
page_type: sample
languages:
- python
products:
- azure
- azure-communication-callautomation
---

#  Call Recording APIs Sample
This is a sample application to showcase how the Call Automation SDK can be used to add recording features to any application.
The application is a console based application build using Python 3.9 and above.
It harnesses the power of Azure Communication Services to establish connections and enable communication features within the application. A separate branch with end to end implementation is [available](https://github.com/Azure-Samples/communication-services-web-calling-hero/tree/public-preview). It's a public preview branch and uses beta SDKs that are not meant for production use. Please use the main branch sample for any production scenarios.

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
- **Note:** Phone number is required to successfully run this sample.

## Clone the code local and update configuration

1. Open an instance of PowerShell, Windows Terminal, Command Prompt or equivalent and navigate to the directory that you'd like to clone the sample to.
2. Run `git clone https://github.com/Azure-Samples/communication-services-python-quickstarts.git`
3. Once you get the code on local machine, navigate to **call-recording/config.ini** file found under the call-recording folder.
4. Update the values for below.

	| Key | Value | Description |
	| -------- | -------- | -------- |
	| `ACSResourceConnectionString`    | \<ACS Connection String>   | Input your ACS connection string in the variable   |
	| `ACSAcquiredPhoneNumber`    | \<ACS Acquired Number>   | Phone number associated with the Azure Communication Service resource   |
	| `CallbackUri`    | \<ngrok url>   | Base url of the app, don't add `/` at end. generate ngrok url as mentioned above.   |


## Code structure

- *./call-recording/Controller/RecordingsController.py* : Server app core logic for calling the recording APIs using Azure Communication Services callautomation SDK
- *./call-recording/App.py* : Entry point for the server app program logic
- *./call-recording/requirements.txt* : Contains dependencies for running and deploying the application

### Setup the Python environment

Create and activate python virtual environment and install required packages using following command in `call-recording` folder.
```
pip install -r requirements.txt
```

## Run app locally

1. Navigate to `call-recording` folder and run `App.py` in debug mode or use command `python ./App.py` to run it from PowerShell, Command Prompt or Unix Terminal
2. Import `call-recording\data\Recordings API.postman_collection.json` file into postman, you get `Recordings API` collection. For details, see [Importing and exporting data](https://learning.postman.com/docs/getting-started/importing-and-exporting-data/)
3. Select `Recordings API`, under Variables, update `HOST_URL` and `TARGET_PHONE_NUMBER` before making calls.

# Step by step guid for testing recording APIs via postman.

Once App is running locally,
1. Create webhook (Follow "Create Webhook for Microsoft.Communication.RecordingFileStatus event" section below )
2. Start a call by invoking Qutbound Call request. 
	- Accept the call on Target PSTN Phone number, Keep call running.
5. Send Request to StartRecording.
	- Recording would be started.
6. (Optional) PauseRecording, ResumeRecording and GetRecordingState.
7. Send Request for StopRecording.
8. Send Request for DownloadRecording from server, only last recorded file will be downloaded.
9. Send Request for DeleteRecording at server.

## Create Webhook for Microsoft.Communication.RecordingFileStatus event
Call Recording enables you to record multiple calling scenarios available in Azure Communication Services by providing you with a set of APIs to start, stop, pause and resume recording. To learn more about it, see [this guide](https://learn.microsoft.com/en-us/azure/communication-services/concepts/voice-video-calling/call-recording). 
1. Navigate to your Communication Service resource on Azure portal and select `Events` from the left side blade.
2. Click `+ Event Subscription` to create a new subscription, provide `Name` field value. 
3. Under Topic details, choose a System Topic or create new, no changes required if its already have topic name.  
4. Under `Event Types` Filter for `Recording File Status Updated(Preview)` event. 
5. Choose `Endpoint Type` as `Web Hook` and provide the public url generated by Ngrok. It would look like `https://2c0a-49-207-209-111.ngrok-free.app/recordingFileStatus`.  
6. Click `Create` to complete the event grid subscription. The subscription is ready when the provisioning status is marked as succeeded.  
**Note:** Application should be running to able to create the `Web Hook` successfully. 
