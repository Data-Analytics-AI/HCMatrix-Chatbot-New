from typing import Dict, Any
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
            return file_system_client
        except Exception as reason:
            raise ConnectionError(f"failed to connect to ADLS {self.container_name} database. with error ::: {reason}")

    def get_file_system_client(self) -> FileSystemClient:
        return self.file_system_client
