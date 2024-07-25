
import os
from data_preprocessing import (
    adls_connection,
    permissions,
    sql_utils
)

from config.params import credentials_config, params_config

adls_credentials_params = credentials_config['adls_credentials']
mysql_credentials_params = credentials_config['mysql_credentials']
data_dir = params_config['data_dir']

def establish_connections():
    auth_adls_conn = adls_connection.ADLSConnection(mysql_credentials_params['staging']['auth_db_name'], adls_credentials_params)
    utils_adls_conn = adls_connection.ADLSConnection(mysql_credentials_params['staging']['utils_db_name'], adls_credentials_params)
    return auth_adls_conn, utils_adls_conn


def create_company_root_dir(data_root_dir: str, company_id: str) -> str:
    company_root_dir = os.path.join(data_root_dir, f"cp_{company_id}")
    if not os.path.exists(company_root_dir):
        os.makedirs(company_root_dir)
    return company_root_dir


def execute(company_id: str, utils_conn, auth_conn):
    if not isinstance(company_id, str):
        raise ValueError("Wrong value passed into the prerpocessor")
    
    company_root_dir = create_company_root_dir(data_dir, company_id)
    permission = permissions.CompanyPermission(
        company_id, company_root_dir, utils_conn, auth_conn)

    
    employee_ids, role_ids = permission.get_all_employee_role_mapper(
        permission.company_files, 
        permission.dataframe_from_adls_file_path
    )

    SQL_DB_ROOT_PATH = os.path.join(company_root_dir, f"cp_{company_id}_sql")
    if not os.path.exists(SQL_DB_ROOT_PATH):
        os.mkdir(SQL_DB_ROOT_PATH)


    company_files_path = permission._get_or_create_company_save_path(company_id)
    for role_id, emp_id in zip(role_ids, employee_ids):
        sql_path = os.path.join(SQL_DB_ROOT_PATH, f"emp_{emp_id}_sql_db.db")
        employee_tables = permission.generate_employee_permission_tables(role_id, emp_id)
        
        sql_utils.csv_to_sqlite(
            company_files_path,
            employee_tables, sql_path
        )

if __name__ == "__main__":
    company_id = "53"

    auth_conn, utils_conn = establish_connections()
    execute(company_id, utils_conn, auth_conn)