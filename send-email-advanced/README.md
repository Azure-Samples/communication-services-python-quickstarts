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
This sample sends an email to the selected recipients of any domain using an [Email Communication Services resource](https://docs.microsoft.com/azure/communication-services/quickstarts/email/create-email-communication-resource).
This is a console application built using python 3.10.6.

Additional documentation for this sample can be found on [Microsoft Docs](https://docs.microsoft.com/azure/communication-services/concepts/email/email-overview).

## Prerequisites

- An Azure account with an active subscription. [Create an account for free](https://azure.microsoft.com/free/?WT.mc_id=A261C142F).
- [Python](https://www.python.org/downloads/) 3.7+.
- An Azure Email Communication Services resource created and ready with a provisioned domain. [Get started with creating an Email Communication Resource](../create-email-communication-resource.md).
- An active Azure Communication Services resource connected to an Email Domain and its connection string. [Get started by connecting an Email Communication Resource with a Azure Communication Resource](../connect-email-communication-resource.md).

> Note: We can also send an email from our own verified domain [Add custom verified domains to Email Communication Service](https://docs.microsoft.com/azure/communication-services/quickstarts/email/add-custom-verified-domains).

### Prerequisite check

- In a terminal or command window, run the `python --version` command to check that Python is installed.
- To view the domains verified with your Email Communication Services resource, sign in to the [Azure portal](https://portal.azure.com/). Locate your Email Communication Services resource and open the **Provision domains** tab from the left navigation pane.

## Code structure

The advanced version of send-email includes the following sub samples.

### Send email with attachments

- ./send-email-advanced/send-email-attachments/send-email-attachments.py

### Send email to multiple recipients

- ./send-email-advanced/send-email-multiple-recipients/send-email-multiple-recipients.py

## Before running the sample for the first time

1. Open an instance of PowerShell, Windows Terminal, Command Prompt or equivalent program and navigate to the directory that you'd like to clone the sample to.
2. `git clone https://github.com/Azure-Samples/communication-services-python-quickstarts.git`

## Create virtual environment

Navigate to the `send-email` directory in the console. Create a virtual environment and activate it using the following commands.

```cmd
python -m venv venv
.\venv\Scripts\activate
```

## Install the packages

Execute the following command to install the SDK.

```cmd
pip install azure-communication-email
```

### Locally configuring the application

Open the corresponding py file of the sample to configure the following settings:

- `connection_string`: Replace `<ACS_CONNECTION_STRING>` with the connection string found within the 'Keys' blade of the Azure Communication Service resource.
- `sender_address`: Replace `<SENDER_EMAIL_ADDRESS>` with the sender email address obtained from the linked domain resource.
- `recipient_address`: Replace `<RECIPIENT_EMAIL_ADDRESS>` with the recipient email address.

## Run Locally

Execute the following command to run the app.

```cmd
python ./<FILENAME>.py
```

## ❤️ Feedback

We appreciate your feedback and energy in helping us improve our services. [Please let us know if you are satisfied with ACS through this survey](https://microsoft.qualtrics.com/jfe/form/SV_5dtYL81xwHnUVue).
