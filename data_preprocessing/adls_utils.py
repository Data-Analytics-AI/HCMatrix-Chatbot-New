import io
import tempfile
import pandas as pd
from typing import List


def list_all_files_by_company_id(company_id, file_system_client):
    paths = file_system_client.get_paths()
    files = [path.name for path in paths if ".csv" in path.name and company_id in path.name.split("/")]
    return files


def list_all_files_by_organization_id(company_id, file_system_client):
    paths = file_system_client.get_paths()
    files = [path.name for path in paths if ".csv" in path.name and company_id in path.name.split("/")]
    return files


def list_files_for_specific_table(table_name, file_system_client):
    paths = file_system_client.get_paths()
    table_folders = [path.name for path in paths if table_name + "/" in path.name and ".csv" in path.name]
    return table_folders


def dataframe_from_adls_file_path(
        file_path, file_system_client,
        process_in_memory=False, col_to_exclude: List[str] = []):
    file_client = file_system_client.get_file_client(file_path)
    if process_in_memory:
        download = file_client.download_file()
        io_file_object = io.BytesIO(download.readall())

        df = pd.read_csv(io_file_object, usecols=lambda col: col not in col_to_exclude)

    else:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            download = file_client.download_file()
            temp_file.write(download.readall())
            temp_file_path = temp_file.name
        save_path = f"{'_'.join(file_path.split('/')[-1].split('_')[:-3])}.csv"
        df = pd.read_csv(temp_file_path, usecols=lambda col: col not in col_to_exclude)
        df.to_csv(save_path, index=False)
    return df
