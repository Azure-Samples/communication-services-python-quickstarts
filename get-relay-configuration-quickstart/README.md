---
page_type: Quickstart
languages:
  - python
products:
  - azure
  - azure-communication-services
urlFragment: communication-network-traversal-python
---

# Azure Communication Services - Network Traversal client library samples for Python

These quickstart programs show how to use the Python client libraries for Azure Communication Services - Network Traversal in some common scenarios.

| **File Name**                                     | **Description**                 |
| ------------------------------------------------- | ------------------------------- |
| [get_relay_configuration.py][getrelayconfiguration] | Issue a new Relay configuration |
| [get_relay_configuration_with_route_type.py][getrelayconfiguration] | Issue a new Relay configuration providing a Route Type|
| [get_relay_configuration_with_identity.py][getrelayconfiguration] | Issue a new Relay configuration providing a User Identity|
| [get_relay_configuration_with_ttl.py][getrelayconfiguration] | Issue a new Relay configuration providing a Ttl|

## Prerequisites

- An Azure account with an active subscription. [Create an account for free](https://azure.microsoft.com/free/?WT.mc_id=A261C142F). 
- [Python](https://www.python.org/downloads/) 3.7, or above.
- A deployed Communication Services resource and connection string. [Create a Communication Services resource](https://docs.microsoft.com/azure/communication-services/quickstarts/create-communication-resource).

 
## Before running quickstart code

To run the quickstarts using the published version of the package:

1. Install the dependencies using `pip`:
```bash
pip install aiortc
pip install azure-communication-networktraversal==1.1.0b1
```
2. Open an instance of PowerShell, Windows Terminal, Command Prompt or equivalent and navigate to the directory that you'd like to clone the sample to.
3. `git clone https://github.com/Azure-Samples/communication-services-python-quickstarts.git`
4. With the Communication Services procured in pre-requisites, add connection string in the code.
6. Run whichever quickstarts you like (note that some quickstarts may require additional setup, see the table above):
```bash
python get_relay_configuration.py
```

## Next Steps

Take a look at our [API Documentation][apiref] for more information about the APIs that are available in the clients:

[getrelayconfiguration]: https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/communication/azure-communication-networktraversal/samples
[freesub]: https://azure.microsoft.com/free/
[createinstance_azurecommunicationservicesaccount]: https://docs.microsoft.com/azure/communication-services/quickstarts/create-communication-resource
[package]: https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/communication/azure-communication-networktraversal/README.md
