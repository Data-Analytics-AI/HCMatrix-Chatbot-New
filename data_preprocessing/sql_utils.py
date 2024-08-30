
from typing import *
import pandas as pd
import sqlite3
import os

def csv_to_sqlite(
    csv_folder: os.PathLike, 
    emp_table_names: Dict[str, List[str]], 
    db_name: Union[str, os.PathLike]
)-> None:
    
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    csv_files = []

    # Process table names
    if emp_table_names.get('table_names'):
        available_files = os.listdir(csv_folder)
        table_names = set(emp_table_names['table_names'])
        csv_files.extend(
            os.path.join(csv_folder, f) 
            for f in available_files 
            # if "_".join(f.split("_")[:-1]) in table_names
            if f.split(".")[0] in table_names
        )

    # Process personal table paths
    if emp_table_names.get('personal_table_path'):
        personal_emp_csv_files = emp_table_names['personal_table_path']
        csv_files.extend(
            os.path.join(csv_folder, f) 
            for f in personal_emp_csv_files
        )

    # Read and insert each CSV file into the SQLite database
    csv_files = list(set(csv_files))
    for csv_file in csv_files:
        base_name = os.path.basename(csv_file)
        table_name = "_".join(base_name.split("_")[:-1]) if csv_file in emp_table_names.get('personal_table_path', []) else os.path.splitext(base_name)[0]
            
        print(f"Importing {csv_file} into table {table_name}")
        df = pd.read_csv(csv_file)
        df.to_sql(table_name, conn, if_exists='replace', index=False)

    conn.commit()
    conn.close()


def print_tables(database_path):
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")    
    tables = cursor.fetchall()
    
    print("Tables in the database:")
    for table in tables:
        print(table[0])
    
    conn.close()


if __name__ == "__main__":
    print_tables("/home/alijoe/Downloads/emp_372_sql_db.db")