import io
import pandas as pd
from typing import List
from azure.storage.filedatalake import FileSystemClient


class DataFrameLoaders:
    def __init__(self, company_id, file_system_client: FileSystemClient) -> None:
        self.company_id = company_id
        self.file_system_client = file_system_client
        valid_substrings = ["employees/", "designations/"]
        self.company_files = self._list_all_files_by_company_id()
        self.data_path = [item for _, item in enumerate(self.company_files) if
                          any(substring in item for substring in valid_substrings)]
        print(self.data_path)

    def load_employee_df(self, ):
        employee_df_path = [q for q in self.data_path if "employees" in q]
        employee_df = self._dataframe_from_adls_file_path(employee_df_path[-1])
        return employee_df

    def load_designation_df(self, ):
        designation_df_path = [q for q in self.data_path if "designations" in q]
        designation_df = self._dataframe_from_adls_file_path(designation_df_path[-1])
        return designation_df

    def load_group_df(self, ):
        group_df = self._dataframe_from_adls_file_path('group_managements/group_managements_20240613_154409.csv')
        return group_df

    def _dataframe_from_adls_file_path(self, file_path):
        file_client = self.file_system_client.get_file_client(file_path)
        download = file_client.download_file()
        io_file_object = io.BytesIO(download.readall())

        df = pd.read_csv(io_file_object)
        return df

    def _list_all_files_by_company_id(self, ):
        paths = self.file_system_client.get_paths()
        files = [path.name for path in paths if ".csv" in path.name and self.company_id in path.name.split("/")]
        return files


class EmployeeIDExtractor(DataFrameLoaders):
    def __init__(self, company_id: str, file_system_client: FileSystemClient) -> None:
        super().__init__(company_id, file_system_client)
        self.designation_table = self.load_designation_df()
        self.employee_table = self.load_employee_df()
        self.group_table = self.load_group_df()

    def extract_employee_ids_from_department_id(self, department_id: int):
        des_ids = self.designation_table[self.designation_table['departmentId'] == department_id]['id'].to_list()
        employee_ids = self.employee_table[self.employee_table['designationId'].isin(des_ids)]['id'].to_list()
        return employee_ids

    def extract_employee_ids_from_role_id(self, role_id: int) -> List[int]:
        employee_ids = self.employee_table[self.employee_table['roleId'] == role_id]['id'].to_list()
        return employee_ids

    def extract_employee_ids_from_group_id(self, grp_id: int):
        employee_ids = self.group_table[self.group_table['groupId'] == grp_id]['employeeId'].to_list()
        return employee_ids
