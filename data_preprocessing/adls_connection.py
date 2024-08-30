
from typing import *
from azure.storage.filedatalake import DataLakeServiceClient, FileSystemClient
from azure.identity import ClientSecretCredential


class ADLSConnection:
    def __init__(self, container_name: str, config_params: Dict[str, Any], account_name: str) -> None:
        self.container_name = container_name
        self.config_params = config_params
        self.account_name = account_name
        self.file_system_client = self._create_file_system_client()

    def _create_file_system_client(self) -> FileSystemClient:
        try:
            credential = ClientSecretCredential(
                self.config_params["tenant_id"], self.config_params["client_id"], 
                self.config_params["client_secret"])
            
            service_client = DataLakeServiceClient(
                account_url=f"https://{self.account_name}.dfs.core.windows.net", 
                credential=credential)
            
            file_system_client = service_client.get_file_system_client(file_system=self.container_name)
            # hcm_logger.info(f"connection esthablished to hcmatrix ADLS {self.container_name} DB")
            return file_system_client
        except Exception as reaseon:
            # hcm_logger.erro(f"failed to connect to ADLS {self.container_name} database. with error ::: {reaseon}")
            raise ConnectionError(f"failed to connect to ADLS {self.container_name} database. with error ::: {reaseon}")

    def get_file_system_client(self) -> FileSystemClient:
        return self.file_system_client
    

# class ADLSConnection:
#     def __init__(self, container_name: str, config_params: Dict[str, Any]) -> None:
#         self.container_name = container_name
#         self.config_params = config_params
#         self.file_system_client: Optional[FileSystemClient] = None

#     def _create_file_system_client(self) -> FileSystemClient:
#         credential = ClientSecretCredential(
#             self.config_params["tenant_id"], self.config_params["client_id"], 
#             self.config_params["client_secret"])
        
#         service_client = DataLakeServiceClient(
#             account_url=f"https://{self.config_params['account_name']}.dfs.core.windows.net", 
#             credential=credential)
        
#         file_system_client = service_client.get_file_system_client(file_system=self.container_name)
#         return file_system_client

#     def __enter__(self) -> FileSystemClient:
#         self.file_system_client = self._create_file_system_client()
#         return self.file_system_client

#     def __exit__(self, exc_type, exc_val, exc_tb) -> None:
#         if self.file_system_client:
#             self.file_system_client.close()
#             self.file_system_client = None

#     def get_file_system_client(self) -> FileSystemClient:
#         if not self.file_system_client:
#             self.file_system_client = self._create_file_system_client()
#         return self.file_system_client


# config_params = {
#     "tenant_id": "your_tenant_id",
#     "client_id": "your_client_id",
#     "client_secret": "your_client_secret",
#     "account_name": "your_account_name"
# }

# container_name = "your_container_name"

# with ADLSConnection(container_name, config_params) as file_system_client:
#     # Use the file_system_client here
#     # Any operations with file_system_client
#     pass
# Automatically closes the connection after the block
