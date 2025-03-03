import io
import aiofiles
from typing import Dict, Any
from module.adls_connection import ADLSConnectionAsync  # Import the async ADLS connection class


class GoldLayerUtilsAsync(ADLSConnectionAsync):
    def __init__(
            self, container_name: str, config_params: Dict[str, Any],
            account_name: str, directory_name: str = "temp_data/"
    ) -> None:
        super().__init__(container_name, config_params, account_name)
        self.directory_name = directory_name

    async def read_file_from_adls(self, adls_file_path: str, read_memory: bool = True):
        """Reads a file from ADLS asynchronously."""
        await self.get_file_system_client()  # Ensure the client is initialized

        blob_client = self.file_system_client.get_blob_client(adls_file_path)

        if read_memory:
            async with aiofiles.tempfile.NamedTemporaryFile(delete=False) as temp_file:
                stream = await blob_client.download_blob()
                content = await stream.readall()
                await temp_file.write(content)
                temp_file_path = temp_file.name
            return temp_file_path
        else:
            stream = await blob_client.download_blob()
            io_file_object = io.BytesIO(await stream.readall())

            async with aiofiles.open('temp_db.db', 'wb') as temp_db_file:
                await temp_db_file.write(io_file_object.getbuffer())
