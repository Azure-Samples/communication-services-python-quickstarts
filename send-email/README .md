---
page_type: sample
languages:
- Python
products:
- azure
- azure-communication-email
---

# Email Sample

## Overview

This is a sample email application to show how we can use the `azure-communication-email` package to build an email experience.
This sample sends an email to the selected recipients of any domain using an [Email Communication Services resource](https://docs.microsoft.com/en-us/azure/communication-services/quickstarts/email/create-email-communication-resource).
This is a console application built using python 3.10.6.

Additional documentation for this sample can be found on [Microsoft Docs](https://pypi.org/project/azure-communication-email).

## Prerequisites

- Python
- Create an Azure account with an active subscription. For details, see [Create an account for free](https://azure.microsoft.com/free/?WT.mc_id=A261C142F).
- Create an Azure Communication Services resource. For details, see [Create an Azure Communication Resource](https://docs.microsoft.com/azure/communication-services/quickstarts/create-communication-resource). You'll need to record your resource **connection string** for this Sample.
- Create an [Azure Email Communication Services resource](https://docs.microsoft.com/en-us/azure/communication-services/quickstarts/email/create-email-communication-resource) to start sending emails.

> Note: We can send an email from our own verified domain also [Add custom verified domains to Email Communication Service](https://docs.microsoft.com/en-us/azure/communication-services/quickstarts/email/add-custom-verified-domains).

## Code Structure

- **./send-email/send-email.py:** contains code for sending emails.

## Before running the sample for the first time

1. Open an instance of PowerShell, Windows Terminal, Command Prompt or equivalent program and navigate to the directory that you'd like to clone the sample to.
2. `git clone https://github.com/Azure-Samples/communication-services-python-quickstarts.git`


## Create virtual environment

Navigate to the `send-email` directory in the console. Create a virtual environment and activate it using the following commands.

```
python -m venv venv
.\venv\Scripts\activate
```

## Install the packages

Execute the following command to install the SDK.

```
pip install azure-communication-email
```

### Locally configuring the application

Open the `send-email.py` file and configure the following settings:

- `connection_string`: Replace `<ACS_CONNECTION_STRING>` with the connection string found within the Azure Communication Service resource.
- `sender_address`: Replace `<SENDER_EMAIL_ADDRESS>` with the sender email address obtained from the linked domain resource.
- `recipient_address`: Replace `<RECIPIENT_EMAIL_ADDRESS>` with the recipient email address.

## Run Locally

Execute the following command to run the app.

```
python ./send-email.py
```

## ❤️ Feedback

We appreciate your feedback and energy in helping us improve our services. [Please let us know if you are satisfied with ACS through this survey](https://microsoft.qualtrics.com/jfe/form/SV_5dtYL81xwHnUVue).
