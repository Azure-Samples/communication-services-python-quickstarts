from azure.storage.blob import BlobServiceClient, BlobClient, generate_blob_sas

import Logger
from BlobStorageHelperInfo import BlobStorageHelperInfo

class BlobStorageHelper():

    def check_container_availability(account_url, container_name):
        client = BlobServiceClient(account_url)

        container = client.get_container_client(container=container_name)
        return container is not None

    def check_blob_availability(account_url, container_name, blob_name):
        client = BlobServiceClient(account_url)

        blob = client.get_blob_client(container=container_name, blob=blob_name)
        return blob is not None

    def upload_file_to_storage(container_name: str, file_name: str, file_type: str, blob_connection_string: str):

        if not BlobStorageHelper.check_container_availability(container_name, file_name):
            container_info = BlobStorageHelperInfo()
            container_info.info = 'Container ->' + container_name + 'is not available'
            return container_info

        if not BlobStorageHelper.check_blob_availability(container_name, file_name):
            blob_info = BlobStorageHelperInfo()
            blob_info.info = 'blob ->' + file_name + 'is not available'
            return blob_info

        blob = BlobClient.from_connection_string(conn_str=blob_connection_string, container_name=container_name,
                                                 blob_name=file_name)

        with open("file", "rb") as data:
            blob.upload_blob(data)

        b = blob
        return 111

    def get_blob_sas_uri(container_name: str, account_name: str, file_name: str):
        data = generate_blob_sas('account name', container_name, file_name)
