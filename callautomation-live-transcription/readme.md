|page_type| languages                               |products
|---|-----------------------------------------|---|
|sample| <table><tr><td>Python</tr></td></table> |<table><tr><td>azure</td><td>azure-communication-services</td></tr></table>|

# Call Automation - Quick Start Sample

This sample application shows how the Azure Communication Services  - Call Automation SDK can be used generate the live transcription between PSTN calls. 
It accepts an incoming call from a phone number, performs DTMF recognition, and transfer the call to agent. You can see the live transcription in websocket during the conversation between agent and user
This sample application is also capable of making multiple concurrent inbound calls. The application is a web-based application built on Python.

## Prerequisites

- Create an Azure account with an active subscription. For details, see [Create an account for free](https://azure.microsoft.com/free/)
- Create an Azure Communication Services resource. For details, see [Create an Azure Communication Resource](https://docs.microsoft.com/azure/communication-services/quickstarts/create-communication-resource). You'll need to record your resource **connection string** for this sample.
- An Calling-enabled telephone number. [Get a phone number](https://learn.microsoft.com/en-us/azure/communication-services/quickstarts/telephony/get-phone-number?tabs=windows&pivots=platform-azp).
- Install ngrok. Instructions [here](https://ngrok.com/)
- Create Azure AI Multi Service resource. For details, see [Create an Azure AI Multi service](https://learn.microsoft.com/en-us/azure/cognitive-services/cognitive-services-apis-create-account).
- An Azure OpenAI Resource and Deployed Model. See [instructions](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/how-to/create-resource?pivots=web-portal).
- [Python](https://www.python.org/downloads/) 3.7 or above.

## Before running the sample for the first time

1. Open an instance of PowerShell, Windows Terminal, Command Prompt or equivalent and navigate to the directory that you would like to clone the sample to.
2. git clone `https://github.com/Azure-Samples/communication-services-python-quickstarts.git`.
3. Navigate to `callautomation-openai-sample` folder and open `main.py` file.

### Setup the Python environment

Create and activate python virtual environment and install required packages using following command 
```
pip install -r requirements.txt
```

### Setup and host ngrok

You can run multiple tunnels on ngrok by changing ngrok.yml file as follows:

1. Open the ngrok.yml file from a powershell using the command ngrok config edit
2. Update the ngrok.yml file as follows:
    authtoken: xxxxxxxxxxxxxxxxxxxxxxxxxx
    version: "2"
    region: us
    tunnels:
    first:
        addr: 8080
        proto: http 
        host_header: localhost:8080
    second:
        proto: http
        addr: 5001
        host_header: localhost:5001
NOTE: Make sure the "addr:" field has only the port number, not the localhost url.
3. Start all ngrok tunnels configured using the following command on a powershell - ngrok start --all
4. Once you have setup the websocket server, note down the the ngrok url on your server's port as the websocket url in this application for incoming call scenario. Just replace the https:// with wss:// and update in the `TRANSPORT_URL` main.py file.

### Configuring application

Open `main.py` file to configure the following settings

1. - `CALLBACK_URI_HOST`: Ngrok url for the server port (in this example port 8080)
2. - `COGNITIVE_SERVICE_ENDPOINT`: The Cognitive Services endpoint
3. - `ACS_CONNECTION_STRING`: Azure Communication Service resource's connection string.
4. - `TRANSPORT_URL`: Ngrok url for the server port (in this example port 5001) make sure to replace https:// with wss://
5. - `ACS_PHONE_NUMBER`: Acs Phone Number
6. - `LOCALE`: Transcription locale
6. - `AGENT_PHONE_NUMBER`: Agent Phone Number to add into the call

## Run app locally

1. Navigate to `callautomation-live-transcription` folder and run `main.py` in debug mode or use command `python ./main.py` to run it from PowerShell, Command Prompt or Unix Terminal
2. Browser should pop up with the below page. If not navigate it to `http://localhost:8080/` or your ngrok url which points to 8080 port.
3. Register an EventGrid Webhook for the IncomingCall(`api/incomingCall`) and for Recording File Status(`api/recordingFileStatus`) Event that points to your ngrok URI. Instructions [here](https://learn.microsoft.com/en-us/azure/communication-services/concepts/call-automation/incoming-call-notification).

Once that's completed you should have a running application. The best way to test this is to place a call to your ACS phone number and talk to your intelligent agent.
