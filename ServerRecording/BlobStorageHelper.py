from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta
import Logger

class BlobStorageHelper():

    def upload_file_to_storage(
        container_name: str,
        blob_name: str,
        blob_connection_string: str
    ):
        blob_service_client = BlobServiceClient.from_connection_string(blob_connection_string)
        container_client = blob_service_client.get_container_client(container=container_name)
        if container_client and not container_client.exists():
            return 'Blob Container -> ' + container_name + ' is unavailable'

        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        if blob_client and blob_client.exists():
            return 'Blob -> ' + blob_name + ' already exists'
        
        if blob_client:
            with open(blob_name, "rb") as data:
                blob_client.upload_blob(data.read())
        else:
            return "Blob client instantiation failed"

        return True

    def get_blob_sas_token(
        account_name: str,
        account_key: str,
        container_name: str,
        blob_name: str
    ):
        try:
            return generate_blob_sas(
                account_name=account_name,
                container_name=container_name,
                blob_name=blob_name,
                account_key=account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(hours=1))
        except Exception as ex:
            Logger.log_message(Logger.ERROR, str(ex))
            return False

    def get_blob_sas_uri(
        account_name: str,
        account_key: str,
        container_name: str,
        blob_name: str
    ):
        blob_sas_token = BlobStorageHelper.get_blob_sas_token(
            account_name,
            account_key,
            container_name,
            blob_name)

        blob_uri_template = 'https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}?{blob_sas_token}'

        return blob_uri_template.format(
            account_name=account_name,
            container_name=container_name,
            blob_name=blob_name,
            blob_sas_token=blob_sas_token)

    


