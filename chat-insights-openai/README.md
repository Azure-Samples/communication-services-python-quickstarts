---
page_type: sample
languages:
- Python
products:
- azure
- azure-communication-services
---


# Generate chat insights using Azure OpenAI

## Prerequisites

- An Azure account with an active subscription. [Create an account for free](https://azure.microsoft.com/free/?WT.mc_id=A261C142F). 
- An active Communication Services resource. You will need its connection string and endpoint. [Create a Communication Services resource](https://docs.microsoft.com/azure/communication-services/quickstarts/create-communication-resource).
- Create an Azure OpenAI resource. See [instructions](https://aka.ms/acs-sms-open-ai-create-open).   
- Deploy an Azure OpenAI model (Can use GPT-3, ChatGPT or GPT-4 models). See [instructions](https://aka.ms/acs-sms-open-ai-deploy-model). 
- [Python](https://www.python.org/downloads/) 3.11.2 or above.

## Install the packages

```bash

pip install openai azure.communication.chat azure.communication.identity

```

## Before running sample code

1. Open an instance of PowerShell, Windows Terminal, Command Prompt or equivalent and navigate to the directory that you'd like to clone the sample to.
2. `git clone https://github.com/Azure-Samples/communication-services-python-quickstarts.git`.
3. With the Communication Services procured in pre-requisites, add connection string, endpoint, Azure OpenAI key and Azure OpenAI endpoint to **chatInsights.py** file.

## Run Locally

From a console prompt, navigate to the directory containing the chatInsights.py file, then execute the following command to run the app.

```bash

python ./chatInsights.py

```