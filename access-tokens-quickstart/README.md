---
page_type: sample
languages:
- Python
products:
- azure
- azure-communication-services
---


# Create and manage access tokens

For full instructions on how to build this code sample from scratch, look at [Quickstart: Create and manage access tokens](https://docs.microsoft.com/en-us/azure/communication-services/quickstarts/access-tokens?pivots=programming-language-python)

## Prerequisites

- An Azure account with an active subscription. [Create an account for free](https://azure.microsoft.com/free/?WT.mc_id=A261C142F). 
- [Python](https://www.python.org/downloads/) 2.7, 3.5, or above.
- An active Communication Services resource and connection string.. [Create a Communication Services resource](https://docs.microsoft.com/en-us/azure/communication-services/quickstarts/create-communication-resource).

## Code Structure

- **./access-tokens-quickstart/issue-access-tokens.py:** contains code for creating and managing access tokens.

## Install the package
pip install azure-communication-identity

## Before running sample code

1. Open an instance of PowerShell, Windows Terminal, Command Prompt or equivalent and navigate to the directory that you'd like to clone the sample to.
2. `git clone https://github.com/Azure-Samples/communication-services-python-quickstarts.git`
3.  With the Communication Services procured in pre-requisites, add connection string to environment variable using below command

    setx COMMUNICATION_SERVICES_CONNECTION_STRING <CONNECTION_STRING>

4. Add pip installation to PATH variables.

## Run Locally

From a console prompt, navigate to the directory containing the issue-access-tokens.py file, then execute the following python command to run the app.

python ./issue-access-tokens.py
