from azure.storage.filedatalake import FileSystemClient
import pandas as pd
import io


class FilePermissions:

    def __init__(self, company_id: str, file_system_client: FileSystemClient) -> None:
        self.company_id = company_id
        self.file_system_client = file_system_client
        self.all_file_path = self._list_files_for_specific_table("files")
        self.file_access_path = self._list_files_for_specific_table("file_access")
        self.company_file_access_df = self._dataframe_from_adls_file_path(self.file_access_path[-1])

    def extract_files_id_for_specific_company(self, ):
        comp_file_path = [i for i in self.all_file_path if f"files/{self.company_id}/" in i]

        files_df = self._dataframe_from_adls_file_path(comp_file_path[-1], self.file_system_client)
        comp_file_ids = files_df['id'].to_list()
        comp_doc_urls = files_df['url'].to_list()
        return comp_file_ids, comp_doc_urls

    def get_document_metadata(self, document_id: int, document_url: str):
        department_pass = self.company_file_access_df[(self.company_file_access_df['fileId'] == document_id) & (
            self.company_file_access_df['type'] == "department")]['entityId'].to_list()
        role_pass = self.company_file_access_df[
            (self.company_file_access_df['fileId'] == document_id) & (self.company_file_access_df['type'] == "role")][
            'entityId'].to_list()
        group_pass = self.company_file_access_df[
            (self.company_file_access_df['fileId'] == document_id) & (self.company_file_access_df['type'] == "group")][
            'entityId'].to_list()

        metadata = {
            "doc_id": document_id,
            "document_url": document_url,
            "department_ids": list(map(str, department_pass)),
            "role_ids": list(map(str, role_pass)),
            "group_ids": list(map(str, group_pass)),
        }

        return metadata

    def get_company_documents_metadata(self, ):
        company_file_ids, company_doc_urls = self.extract_files_id_for_specific_company()
        company_documents_metadata = []

        for file_id, urls in zip(company_file_ids, company_doc_urls):
            company_documents_metadata.append(self.get_document_metadata(file_id, urls))

        return company_documents_metadata

    def _dataframe_from_adls_file_path(self, file_path):
        file_client = self.file_system_client.get_file_client(file_path)
        download = file_client.download_file()
        io_file_object = io.BytesIO(download.readall())

        df = pd.read_csv(io_file_object)
        return df

    def _list_files_for_specific_table(self, table_name):
        paths = self.file_system_client.get_paths()
        table_folders = [path.name for path in paths if table_name + "/" in path.name and ".csv" in path.name]
        return table_folders
