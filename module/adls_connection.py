from azure.storage.blob.aio import BlobServiceClient
from azure.identity.aio import ClientSecretCredential
from typing import Dict, Any, Optional


class ADLSConnectionAsync:
    def __init__(self, container_name: str, config_params: Dict[str, Any], account_name: str) -> None:
        """
        Initializes an async connection to Azure Data Lake Storage (ADLS).

        Args:
            container_name (str): The name of the ADLS container.
            config_params (Dict[str, Any]): Dictionary containing 'tenant_id', 'client_id', and 'client_secret'.
            account_name (str): The name of the Azure storage account.

        Attributes:
            service_client (Optional[BlobServiceClient]): Blob service client for ADLS access.
            file_system_client (Optional[Any]): Container client for file operations.
            credential (Optional[ClientSecretCredential]): Azure authentication credentials.
        """
        self.container_name = container_name
        self.config_params = config_params
        self.account_name = account_name
        self.service_client: Optional[BlobServiceClient] = None
        self.file_system_client = None
        self.credential: Optional[ClientSecretCredential] = None

    async def initialize_client(self) -> None:
        """Initializes the ADLS async client with authentication."""
        try:
            self.credential = ClientSecretCredential(
                tenant_id=self.config_params["tenant_id"],
                client_id=self.config_params["client_id"],
                client_secret=self.config_params["client_secret"]
            )

            self.service_client = BlobServiceClient(
                account_url=f"https://{self.account_name}.blob.core.windows.net",
                credential=self.credential
            )

            self.file_system_client = self.service_client.get_container_client(self.container_name)

        except Exception as reason:
            self.credential = None  # Cleanup
            raise ConnectionError(f"Failed to connect to ADLS {self.container_name}. Error: {reason}")

    async def get_file_system_client(self):
        """Ensures the client is initialized before usage."""
        if not self.file_system_client:
            await self.initialize_client()
        return self.file_system_client

    async def close(self) -> None:
        """Closes the ADLS client session and cleans up credentials."""
        if self.service_client:
            self.service_client = None  # No async close() method in BlobServiceClient

        if self.credential:
            await self.credential.close()  # Close the credential session
            self.credential = None  # Cleanup reference
