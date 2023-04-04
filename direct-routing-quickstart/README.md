---
page_type: sample
languages:
- Python
products:
- azure
- azure-communication-services
---


# Direct Routing Configuration

For full instructions on how to build this code sample from scratch, look at [Quickstart: Direct Routing](https://docs.microsoft.com/azure/communication-services/quickstarts/telephony-sms/voice-routing-sdk-config?pivots=programming-language-python)

## Prerequisites

- An Azure account with an active subscription. [Create an account for free](https://azure.microsoft.com/free/?WT.mc_id=A261C142F). 
- [Python](https://www.python.org/downloads/) 3.7 or above.
- A deployed Communication Services resource and connection string. [Create a Communication Services resource](https://docs.microsoft.com/azure/communication-services/quickstarts/create-communication-resource).

## Code Structure

- *./direct-routing-quickstart/direct_routing_sample.py* contains code for Direct Routing configuration.

## Install the packages

pip install azure-communication-phonenumbers==1.1.0

pip install azure-identity

## Before running sample code

1. Open an instance of PowerShell, Windows Terminal, Command Prompt or equivalent and navigate to the directory that you'd like to clone the sample to.
2. `git clone https://github.com/Azure-Samples/communication-services-python-quickstarts.git`
3. With the Communication Services procured in pre-requisites, add connection string in the code.

## Run Locally

From a console prompt, navigate to the directory containing the *direct_routing_sample.py* file, then execute the following command to run the app.

```console
python ./direct_routing_sample.py
```
