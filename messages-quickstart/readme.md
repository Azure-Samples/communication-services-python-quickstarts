---
page_type: sample
languages:
- Python

Products:
- azure
- azure-communication-messages
---

# Advanced Messages quick start

For full instructions on how to build this code sample from scratch, look at [Quickstart: Send WhatsApp Messages](https://learn.microsoft.com/azure/communication-services/quickstarts/advanced-messaging/whatsapp/get-started?pivots=programming-language-python)

## Prerequisites

- An Azure account with an active subscription. [Create an account for free](https://azure.microsoft.com/free/?WT.mc_id=A261C142F).
- Install [Python](https://www.python.org/downloads/) 3.7 or above.
- Create an Azure Communication Services resource. For details, see [Quickstart: Create and manage Communication Services resources](https://docs.microsoft.com/azure/communication-services/quickstarts/create-communication-resource). You'll need to record your resource endpoint for this quickstart.
- Active WhatsApp phone number to receive messages.
- [WhatsApp Business Account registered with your Azure Communication Services resource](/azure/communication-services/quickstarts/advanced-messaging/whatsapp/connect-whatsapp-business-account)

## Code Structure
To run any sample, please select the respective python script.
- **./messages-quickstart/send_text_notification_messages.py:** contains sample code for sending whatsapp messages.

## Install the packages

From a console prompt, navigate to the directory containing the messages-quickstart.py file, then execute the following command:

```console
pip install azure-communication-messages
```

## Before running sample code

1. Open an instance of PowerShell/Windows Terminal/Command Prompt or equivalent and navigate to the directory that you'd like to clone the sample to.
2. `git clone https://github.com/Azure-Samples/communication-services-python-quickstarts.git`
3. `cd communication-services-python-quickstarts/messages-quickstart`
4. With the Communication Services procured in pre-requisites, set environment variables as needed in Sample file and update the same in **send_text_notification_messages.py** file.

## Run Locally

From a console prompt, navigate to the directory containing the send_text_notification_messages.py file, then execute the following command to run the app.

```python
python ./send_text_notification_messages.py
```

Note: Please follow the same approach for running any Sample.
