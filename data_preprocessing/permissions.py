
import os
from typing import *

from data_preprocessing.adls_utils import list_all_files_by_company_id
from data_preprocessing.adls_connection import ADLSConnection
from data_preprocessing.dataloader import DataLoaders
from constants import (
    general_access_tables,
    personal_access_table,
    role_access_table,
    role_table_mapper,
    valid_roles
)

class CompanyPermission(DataLoaders):
    def __init__(self, company_id:str, company_data_dir: str, utility_adls_connection: ADLSConnection, auth_adls_conn: ADLSConnection) -> None:
        super().__init__(utility_adls_connection)

        if not isinstance(company_id, str):
            raise TypeError(f"Company ID should be <class 'str'> and not type {type(company_id)}")

        self.company_id = company_id
        self.auth_adls_conn = auth_adls_conn
        self.company_data_dir = company_data_dir
        self.utility_adls_connection = utility_adls_connection
        self._GENERAL_ACCESS_TABLE = general_access_tables.GENERAL_ACCESS_TABLE
        self._ROLE_ACCESS_TABLE = role_access_table.ROLE_ACCESS_TABLE
        self._ROLE_TABLE_MAPPER = role_table_mapper.ROLE_TABLE_MAPPER
        self._VALID_ROLES_REQUIRED_BOT = valid_roles.VALID_ROLES_REQUIRED_BOT
        self._PERSONAL_ACCESS_TABLE = personal_access_table.PERSONAL_ACCESS_TABLE
        self.company_files = list_all_files_by_company_id(self.company_id, self.file_system_client)
        self.valid_companies_table = [i.split("/")[0] for i in self.company_files]
        self.company_general_access_table = list(set(self.valid_companies_table).intersection(set(self._GENERAL_ACCESS_TABLE)))
        self.company_roles_access_table = list(set(self.valid_companies_table).intersection(set(self._ROLE_ACCESS_TABLE)))
        self.comapny_save_path = self._get_or_create_company_save_path(self.company_id)
        self.download_company_database_adls(self.comapny_save_path, self.company_files)
        self._initialize_data_read_from_adls()


    def _initialize_data_read_from_adls(self):
        self.permission_df = self.dataframe_from_adls_file_path(
            "permissions/permissions.csv", process_in_memory=True,
            adls_connection=self.auth_adls_conn)
        self.roles_df = self.dataframe_from_adls_file_path(
            "role_permissions/role_permissions.csv", process_in_memory=True,
            adls_connection=self.auth_adls_conn)


    def _role_permission_labels_mapper(self, role_id: int):

        permission_ids:list[int] = self.roles_df[self.roles_df['roleId'] == role_id]['permissionId'].to_list()
        permission_labels: list[str] = [self.permission_df[self.permission_df['id'] == id]['name'].iloc[0] for id in permission_ids]
        permission_labels = list(set(permission_labels).intersection(set(self._VALID_ROLES_REQUIRED_BOT)))

        if len(permission_labels) == 0:
            # return ("This user does not have any valid permissions")
            return -1
        else:
            # return (f"This user has the following valid permissions: \n{permission_labels}")
            return permission_labels

    def _get_or_create_company_save_path(self, company_id):
        company_save_path = os.path.join(self.company_data_dir, f"cp_{company_id}_files_remove")
        if not os.path.exists(company_save_path):
            os.mkdir(company_save_path)
        return company_save_path

    def get_valid_table_for_role_id(self, role_id: int) -> Optional[int | List[str]]:
        permission_labels = self._role_permission_labels_mapper(role_id)
        if permission_labels == -1:
            return self._GENERAL_ACCESS_TABLE
        
        elif isinstance(permission_labels, list):
            role_access_tables = []
            for label in permission_labels:
                role_access_tables.extend(self._ROLE_TABLE_MAPPER[label])

            access_tables = [*self._GENERAL_ACCESS_TABLE, *role_access_tables]
            return access_tables
    
    def _employee_role_id_mapper(self, employee_id):
        index = next((i for i, item in enumerate(self.company_files) if "employees/" in item), -1)
        self.employee_df = self.dataframe_from_adls_file_path(self.company_files[index])
        return self.employee_df[self.employee_df["id"] == employee_id]["roleId"].iloc[0]

    @classmethod
    def get_all_employee_role_mapper(cls, company_files, dataframe_from_adls_file_path):
        index = next((i for i, item in enumerate(company_files) if "employees/" in item), -1)
        if index == -1:
            raise ValueError("No employee file found in the company files")
        
        employee_df = dataframe_from_adls_file_path(company_files[index])
        valid_company_employee_ids = employee_df['id'].to_list()
        valid_company_role_ids = employee_df['roleId'].to_list()

        return valid_company_employee_ids, valid_company_role_ids
        
    def extract_personal_employee_data(self, employee_id: int, table: str):
        table_path = next((item for _, item in enumerate(self.company_files) if table in item), -1)
        if table_path != -1:
            save_path = f"{self.comapny_save_path}/{table}_emp-{employee_id}.csv"
            df = self.dataframe_from_adls_file_path(table_path)
            df = df[df["employeeId"] == employee_id]
            
            # It will be empty if the user does not have personal data in the table
            if not df.empty:
                # print ("He's got some data here!!")
                df.to_csv(save_path, index=False)
                return save_path
            # print ("Hes empty")
    

    def generate_employee_permission_tables(self, role_id: int, employee_id: int) -> Dict[str, List[str]]:
            
        emp_table_names = {
            "table_names": [],
            "personal_table_path": []
        }

        employee_valid_tables = self.get_valid_table_for_role_id(role_id)
        emp_table_names['table_names'].extend(employee_valid_tables)
        is_personal_access_table_false = list(set(self._PERSONAL_ACCESS_TABLE) - (set(employee_valid_tables)))
        # print (is_personal_access_table_false)
        for table in is_personal_access_table_false:
            df_path = self.extract_personal_employee_data(employee_id, table)
            if df_path != None:
                emp_table_names['personal_table_path'].append(df_path)
        
        return emp_table_names
    
    
