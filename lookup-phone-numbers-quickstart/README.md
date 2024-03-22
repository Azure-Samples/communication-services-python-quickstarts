---
page_type: sample
languages:
- Python
products:
- azure
- azure-communication-services
---


# Manage Phone Numbers

For full instructions on how to build this code sample from scratch, look at [Quickstart: Look Up Phone Numbers](https://learn.microsoft.com/en-us/azure/communication-services/quickstarts/telephony/number-lookup?pivots=programming-language-python)

## Prerequisites

- An Azure account with an active subscription. [Create an account for free](https://azure.microsoft.com/free/?WT.mc_id=A261C142F). 
- [Python](https://www.python.org/downloads/) 3.7 or above.
- A deployed Communication Services resource and connection string. [Create a Communication Services resource](https://learn.microsoft.com/en-us/azure/communication-services/quickstarts/create-communication-resource).

## Code Structure

- **./lookup-phone-numbers-quickstart/number-lookup-sample.py:** contains code for looking up phone numbers.

## Install the packages

pip install azure-communication-phonenumbers==1.2.0b2

pip install azure-identity

## Before running sample code

1. Open an instance of PowerShell, Windows Terminal, Command Prompt or equivalent and navigate to the directory that you'd like to clone the sample to.
2. `git clone https://github.com/Azure-Samples/communication-services-python-quickstarts.git`
3. With the Communication Services procured in pre-requisites, add connection string as an environment variable named `COMMUNICATION_SERVICES_CONNECTION_STRING`
4.  Decide which lookup you would like to perform, and keep in mind that looking up all the operator details incurs a cost, while looking up only number formatting is free.

> [!WARNING]
> If you want to avoid incurring a charge, comment out lines 22-32
> 
## Run Locally

From a console prompt, navigate to the directory containing the number-lookup-sample.py file, then execute the following command to run the app, replacing `<target-phone-number` with the number you want to look up.

python ./number-lookup-sample.py <target-phone-number>

