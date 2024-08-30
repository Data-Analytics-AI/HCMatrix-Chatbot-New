
import os
import io
import shutil
import tempfile
from typing import *
from data_preprocessing.adls_connection import ADLSConnection
from config.params import params_config

class GoldLayerUtils(ADLSConnection):
    def __init__(
        self, container_name: str, config_params: Dict[str, Any], 
        account_name: str, directory_name: str ="temp_data/", ### onlie directory
        local_temp_dir: str = "temp_data/" # params_config["data_dir"]
    ) -> None:
        
        super().__init__(container_name, config_params, account_name)
        self.directory_name: str = directory_name 
        self.local_temp_dir: str = local_temp_dir
        self.client_directory = self.create_directory()
        # self.delete_adls_directory()

    def create_directory(self):
        client_directory = self.file_system_client.create_directory(self.directory_name)
        return client_directory

    def delete_adls_directory(self):
        # if os.path.exists(self.directory_name):
        #     for item_name in os.listdir(self.directory_name):
        #         item_path = os.path.join(self.directory_name, item_name)
        #         shutil.rmtree(item_path)

        self.client_directory.delete_directory(self.directory_name)
    
    def get_all_files(self, local_temp_dir, visited = set()):
        for directory_entity in os.listdir(local_temp_dir):
            directory_entity_path = os.path.join(local_temp_dir, directory_entity)
            if os.path.isfile(directory_entity_path) and directory_entity not in visited:
                visited.add(directory_entity_path)
            else:
                self.get_all_files(directory_entity_path)
        return visited

    def upload_file_to_adls(self, local_file_path):
        file_client = self.client_directory.create_file(local_file_path.removeprefix(self.directory_name))
        with open(local_file_path, "rb") as file_data:
            file_client.upload_data(file_data, overwrite=True)
        return local_file_path
    
    def upload_folder_to_adls(self):
        all_company_files = self.get_all_files(self.local_temp_dir)
        all_company_files = [i for i in list(all_company_files) if i.endswith("db")] # only use ".db"files
        all_uploaded_files = []
        print (all_company_files)
        for filepath in all_company_files:
            print (f"{filepath} uploaded to ADLS Gold Layer")
            file_uploaded = self.upload_file_to_adls(filepath)
            all_uploaded_files.append(file_uploaded)

    def read_file_from_adls(self, adls_file_path: str, read_memory: bool = True):
        file_client = self.file_system_client.get_file_client(adls_file_path)

        if read_memory:
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                download = file_client.download_file()
                temp_file.write(download.readall())
                temp_file_path = temp_file.name

            # conn = sqlite3.connect(temp_file_path)
            # cur = conn.cursor()

            return temp_file_path
        
        else:
            download = file_client.download_file()
            io_file_object = io.BytesIO(download.readall())

            with open('temp_db.db', 'wb') as temp_db_file:
                temp_db_file.write(io_file_object.getbuffer())
            


if __name__ == "__main__":
    from config.params import credentials_config
    from langchain_community.utilities import SQLDatabase

    adls_credentials_params     = credentials_config['adls_credentials']
    gold_container_name         = credentials_config['adls_credentials']['goldlayer_container_name']
    gold_account_name           = credentials_config['adls_credentials']['goldlayer_account_name']
    gold_adls_conn  = GoldLayerUtils(gold_container_name, adls_credentials_params, gold_account_name)
    sql_db = gold_adls_conn.read_file_from_adls("temp_data/cp_53/cp_53_sql/emp_373_sql_db.db")
    employee_db = SQLDatabase.from_uri(f"sqlite:///{sql_db}")
    print (employee_db.get_usable_table_names())
