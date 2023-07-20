page_type: sample
languages:
- Python

Products:
- azure
- azure-communication-jobrouter
---

# Job Router quick start

For full instructions on how to build this code sample from scratch, look at [Quickstart: Create a worker and job](https://learn.microsoft.com/azure/communication-services/quickstarts/jobrouter/quickstart)

## Prerequisites

- An Azure account with an active subscription. [Create an account for free](https://azure.microsoft.com/free/?WT.mc_id=A261C142F).
- Install [Python](https://www.python.org/downloads/) 3.7 or above.
- Create an Azure Communication Services resource. For details, see [Quickstart: Create and manage Communication Services resources](https://docs.microsoft.com/azure/communication-services/quickstarts/create-communication-resource). You'll need to record your resource endpoint for this quickstart.

## Code Structure

- **./jobrouter-quickstart/router-quickstart.py:** contains sample code.

## Install the packages

From a console prompt, navigate to the directory containing the router-quickstart.py file, then execute the following command:

- pip install azure-communication-jobrouter

## Before running sample code

1. Open an instance of PowerShell/Windows Terminal/Command Prompt or equivalent and navigate to the directory that you'd like to clone the sample to.
2. `git clone https://github.com/Azure-Samples/communication-services-python-quickstarts.git`
3. `cd communication-services-python-quickstarts/jobrouter-quickstart`
4. With the Communication Services procured in pre-requisites, add connection string in **router-quickstart.py** file ```connection_string = '<connection_string>'```.

## Run Locally

From a console prompt, navigate to the directory containing the router-quickstart.py file, then execute the following command to run the app.

python ./router-quickstart.py
