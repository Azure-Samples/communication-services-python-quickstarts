|page_type| languages                               |products
|---|-----------------------------------------|---|
|sample| <table><tr><td>Python</tr></td></table> |<table><tr><td>azure</td><td>azure-communication-services</td></tr></table>|

# Call Automation - Quick Start Sample

This is a sample application that demonstrates the integration of **Azure Communication Services (ACS)** with **Microsoft Copilot Studio (MCS)** bot using the **Direct Line API**. It enables real-time transcription of calls and interaction with a MCS bot, with responses played back to the caller using SSML (Speech Synthesis Markup Language).

## Prerequisites

- **Azure Account**: Create an Azure account with an active subscription. For details, see [Create an account for free](https://azure.microsoft.com/free/).
- **Azure Communication Services Resource**: Create an ACS resource. For details, see [Create an Azure Communication Resource](https://docs.microsoft.com/azure/communication-services/quickstarts/create-communication-resource). Record your resource **connection string** for this sample.
- **Calling-Enabled Phone Number**: Obtain a phone number. For details, see [Get a phone number](https://learn.microsoft.com/en-us/azure/communication-services/quickstarts/telephony/get-phone-number?tabs=windows&pivots=platform-azp).
- **Azure Cognitive Services Resource**: Set up a Cognitive Services resource. For details, see [Create a Cognitive Services resource](https://learn.microsoft.com/en-us/azure/cognitive-services/cognitive-services-apis-create-account).
- **MCS Bot Framework**: Create a MCS bot and enable the **Direct Line channel**. Obtain the **Direct Line secret**.
- **Azure Dev Tunnels CLI**: Install and configure Azure Dev Tunnels. For details, see [Enable dev tunnel](https://learn.microsoft.com/en-us/azure/developer/dev-tunnels/get-started?tabs=windows).

## Before running the sample for the first time

1. Open an instance of PowerShell, Windows Terminal, Command Prompt or equivalent and navigate to the directory that you would like to clone the sample to.
2. git clone `https://github.com/Azure-Samples/communication-services-python-quickstarts.git`.
3. Navigate to `callautomation-mcs-sample` folder and open `main.py` file.

### Setup the Python environment

[Optional] Create and activate python virtual environment and install required packages using following command 
```
python -m venv venv
venv\Scripts\activate
```
Install the required packages using the following command
```
pip install -r requirements.txt
```

### Setup and host your Azure DevTunnel

[Azure DevTunnels](https://learn.microsoft.com/en-us/azure/developer/dev-tunnels/overview) is an Azure service that enables you to share local web services hosted on the internet. Use the commands below to connect your local development environment to the public internet. This creates a tunnel with a persistent endpoint URL and which allows anonymous access. We will then use this endpoint to notify your application of calling events from the ACS Call Automation service.

```bash
devtunnel create --allow-anonymous
devtunnel port create -p 8080
devtunnel host
```

### Configuring application

Create a `.env` file in the project root and add the following settings:

```plaintext
ACS_CONNECTION_STRING=<your_acs_connection_string>
COGNITIVE_SERVICE_ENDPOINT=<your_cognitive_services_endpoint>
DIRECT_LINE_SECRET=<your_direct_line_secret>
BASE_URI=<your_dev_tunnel_uri>  # e.g., https://your-dev-tunnel-url
```

## Run app locally

1. Navigate to `callautomation-msc-sample` folder and run `main.py` in debug mode or use command `python ./main.py` to run it from PowerShell, Command Prompt or Unix Terminal
2. Browser should pop up with the below page. If not navigate it to `http://localhost:8080/` or your ngrok url which points to 8080 port.
4. Register an EventGrid Webhook for the IncomingCall(`https://<devtunnelurl>/api/incomingCall`). Instructions [here](https://learn.microsoft.com/en-us/azure/communication-services/concepts/call-automation/incoming-call-notification).

Once these steps are completed, you should have a running application. To test the application, place a call to your ACS phone number and interact with your intelligent agent.