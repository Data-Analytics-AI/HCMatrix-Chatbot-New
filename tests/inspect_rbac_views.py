"""Inspect RBAC views - ASCII safe output."""
import mysql.connector

conn = mysql.connector.connect(
    host="hcmatrix3db.mysql.database.azure.com",
    port=3306,
    user="csihub",
    password="@Admin123456@",
    database="hcmatrix-utility-db",
    ssl_disabled=False,
)
cursor = conn.cursor()

# Sample rows from v_user_roles
print("Sample rows from v_user_roles (LIMIT 5):")
cursor.execute("SELECT * FROM `v_user_roles` LIMIT 5")
col_names = [desc[0] for desc in cursor.description]
print(f"  Columns: {col_names}")
for row in cursor.fetchall():
    print(f"  ROW: {row}")

# Look up the specific employee 1221
print("\nRows for employee 1221:")
cursor.execute("SELECT * FROM `v_user_roles` WHERE companyId = 1 AND employeeId = 1221")
for row in cursor.fetchall():
    print(f"  ROW: {row}")

# Check other RBAC views and procedures
for view_name in ["v_department_tree", "v_reporting_tree"]:
    print(f"\n--- {view_name} ---")
    try:
        cursor.execute(f"DESCRIBE `{view_name}`")
        for row in cursor.fetchall():
            print(f"  - {row[0]:30s}  {row[1]}")
    except Exception as e:
        print(f"  NOT FOUND or ERROR: {e}")

# Inspect the sp_accessible_employees stored procedure
print("\n--- sp_accessible_employees (stored procedure) ---")
try:
    cursor.callproc("sp_accessible_employees", args=("1221", "1"))
    for result in cursor.stored_results():
        col_names = [desc[0] for desc in result.description]
        print(f"  Columns: {col_names}")
        for row in result.fetchall():
            print(f"  ROW: {row}")
except Exception as e:
    print(f"  NOT FOUND or ERROR: {e}")

cursor.close()
conn.close()
