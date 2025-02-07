from data_preprocessing.adls_connection import ADLSConnection
from typing import List
import pandas as pd
import tempfile
import io
import os


class DataLoaders:
    def __init__(self, adls_connection: ADLSConnection) -> None:
        self.file_system_client = adls_connection.get_file_system_client()
        self.cols_to_exclude = ['createdAt', 'updatedAt']

    def dataframe_from_adls_file_path(
            self, file_path: str, process_in_memory: bool = False,
            cols_to_exclude: List[str] = [], adls_connection: ADLSConnection = None) -> pd.DataFrame:

        if adls_connection:
            file_system_client = adls_connection.get_file_system_client()
        else:
            file_system_client = self.file_system_client

        file_client = file_system_client.get_file_client(file_path)

        if process_in_memory:
            download = file_client.download_file()
            io_file_object = io.BytesIO(download.readall())
            df = pd.read_csv(io_file_object, usecols=lambda col: col not in self.cols_to_exclude)
        else:
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                download = file_client.download_file()
                temp_file.write(download.readall())
                temp_file_path = temp_file.name

            df = pd.read_csv(temp_file_path, usecols=lambda col: col not in self.cols_to_exclude)

        return df

    def download_company_database_adls(self, save_path, company_files: List[str]) -> None:
        file_system_client = self.file_system_client

        for file_path in company_files:
            file_client = file_system_client.get_file_client(file_path)
            download = file_client.download_file()
            io_file_object = io.BytesIO(download.readall())
            df = pd.read_csv(io_file_object, usecols=lambda col: col not in self.cols_to_exclude)
            # save_file_name = f"{'_'.join(file_path.split('/')[-1].split('_')[:-3])}.csv"
            save_file_name = file_path.split('/')[-1]
            df.to_csv(os.path.join(save_path, save_file_name), index=False)
