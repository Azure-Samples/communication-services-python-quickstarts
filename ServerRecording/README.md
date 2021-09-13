---
page_type: sample
languages:
- Python
products:
- azure
- azure-communication-services
---

# Recording APIs sample

This is a sample application to show how the Azure Communication Services server calling SDK can be used to build a call recording feature.

It's a Python based application that connects with Azure Communication Services.

## Prerequisites

- Create an Azure account with an active subscription. For details, see [Create an account for free](https://azure.microsoft.com/free/?WT.mc_id=A261C142F)
- [Visual Studio Code](https://code.visualstudio.com/)
- [Python 3.9 ](https://www.python.org/downloads/release/python-390/) (Make sure to install the version that corresponds with your visual studio code instance, 32 vs 64 bit)
- Create an Azure Communication Services resource. For details, see [Create an Azure Communication Resource](https://docs.microsoft.com/azure/communication-services/quickstarts/create-communication-resource). You'll need to record your resource **connection string** for this quickstart.
- An Azure storage account and container, for details, see [Create a storage account](https://docs.microsoft.com/azure/storage/common/storage-account-create?tabs=azure-portal). You'll need to record your storage **connection string** and **container name** for this quickstart.
- Create a webhook and subscribe to the recording events. For details, see [Create webhook](https://docs.microsoft.com/azure/communication-services/quickstarts/voice-video-calling/download-recording-file-sample)

- [Install Docker](https://docs.docker.com/desktop/windows/install/)

## Code structure

- ./ServerRecording/Controllers : Server app core logic for calling the recording APIs using Azure Communication Services server calling SDK
- ./ServerRecording/App.py : Entry point for the server app program logic
- ./ServerRecording/requirement.txt : Contains dependencies for running and deploying the application

## Before running the sample for the first time

1. Open an instance of PowerShell, Windows Terminal, Command Prompt or equivalent and navigate to the directory that you'd like to clone the sample to.
2. git clone https://github.com/Azure-Samples/communication-services-python-quickstarts.
3. Once you get the config keys add the keys to the **ServerRecording/config.ini**  file found under the Main folder.
	- Input your ACS connection string in the variable `Connectionstring`
	- Input your storage connection string in the variable `BlobStorageConnectionString`
	- Input blob container name for recorded media in the variable `ContainerName`
	- Input recording callback url for start recording api in the variable `CallbackUri`
	- Input your blob storage account name in the variable `BlobStorageAccountName`, it can be derived from the `BlobStorageConnectionString`
	- Input your blob storage account key in the variable `BlobStorageAccountKey`, it can be derived from the `BlobStorageConnectionString`

## Locally running the sample app

1. Go to ServerRecording folder and open `App.py` in Visual Studio code.
2. Run `App.py` from the Run > Start debugging.
3. Use postman or any debugging tool and open url - http://0.0.0.0:5000/.

## Deploying the sample app on Azure
	
Follow this to create azure container registry - [Create an Azure container registry using the Azure portal](https://docs.microsoft.com/azure/container-registry/container-registry-get-started-portal)

Below steps are to create and push docker image to Azure container registry in using Visual studio Code:

**Note**: All commands are run in root directory of project where we have App.py file.

1. Login to Azure using :

		 az login 

1. Login to the Azure container registry using :

		 az acr login --name <registry-name> 

1. Build the docker file to create docker image using :

		 docker build -f Dockerfile -t <docker-image-name>:latest .

1. Push the docker image to Azure container registry using :

		docker push <registry-name>.azurecr.io/<docker-image-name>:latest

	Note the digest Id from the terminal after push is complete.

1. Create web app using docker image <docker-image-name> generated and pushed in above step, follow this for detail : [Deploy to Azure Web App for Containers](https://docs.microsoft.com/azure/devops/pipelines/apps/cd/deploy-docker-webapp)

	We can use same image name for redeployment, we can see the option to redeploy in the Deployment Center option of App Service in Azure portal.		

1. Check the digest id after push command and compare that with on server, we can see digest Id of App in the Log streams of the App service, they should be same.


### Troubleshooting

1. Solution doesn't build, it throws errors during build

	- Check if the azure SDK is installed.
	- Check if all the dependencies are installed as mentioned in requirement.txt
	- Check the digest id after push command and compare that with on server, the digest id on server should match with the latest push digest. We can get server digest Id on the log stream section of the App service. 


**Note**: While you may use http://localhost for local testing, Some of the features will work only after deployment on Azure.

## Additional Reading

- [Azure Communication Calling SDK](https://docs.microsoft.com/azure/communication-services/concepts/voice-video-calling/calling-sdk-features) - To learn more about the Calling Web SDK