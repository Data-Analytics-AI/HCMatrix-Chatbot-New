from azure.storage.blob.aio import BlobServiceClient
from azure.identity.aio import ClientSecretCredential
from typing import Dict, Any


class ADLSConnectionAsync:
    def __init__(self, container_name: str, config_params: Dict[str, Any], account_name: str) -> None:
        self.container_name = container_name
        self.config_params = config_params
        self.account_name = account_name
        self.service_client: BlobServiceClient | None = None  # Ensure it exists
        self.file_system_client = None  # Will be initialized asynchronously
        self.credential: ClientSecretCredential | None = None  # Store credential for cleanup

    async def initialize_client(self):
        """Initializes the ADLS async client."""
        try:
            self.credential = ClientSecretCredential(
                self.config_params["tenant_id"],
                self.config_params["client_id"],
                self.config_params["client_secret"]
            )

            self.service_client = BlobServiceClient(
                account_url=f"https://{self.account_name}.blob.core.windows.net",
                credential=self.credential
            )

            self.file_system_client = self.service_client.get_container_client(self.container_name)
        except Exception as reason:
            raise ConnectionError(f"Failed to connect to ADLS {self.container_name}. Error: {reason}")

    async def get_file_system_client(self):
        """Ensures the client is initialized before usage."""
        if self.file_system_client is None:
            await self.initialize_client()
        return self.file_system_client

    async def close(self):
        """Closes the ADLS client session and credentials."""
        if self.service_client:
            await self.service_client.close()  # Properly close the service client
        if self.credential:
            await self.credential.close()  # Properly close the credential client
