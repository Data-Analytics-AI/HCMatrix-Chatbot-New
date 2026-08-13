"""
Quick RBAC test - verifies sp_accessible_employees stored procedure works
for employeeId=1, companyId=1.
"""
import asyncio
import sys
import os

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from module.utils import config
from module.rbac_service import resolve_rbac_context
from urllib.parse import quote_plus
from sqlalchemy import create_engine

# Build the DB URI from config (same as app.py)
db_creds = config["production"]["chatbot_db_credentials"]
_encoded_password = quote_plus(str(db_creds['password']))
_port = int(db_creds['port'])

CHATBOT_DB_BASE_URI = (
    f"mysql+mysqlconnector://{db_creds['user']}:{_encoded_password}"
    f"@{db_creds['host']}:{_port}/"
)

engine = create_engine(CHATBOT_DB_BASE_URI, pool_pre_ping=True)

async def main():
    company_id = "1"
    employee_id = "1"

    print(f"Testing RBAC resolution for companyId={company_id}, employeeId={employee_id}")
    print("=" * 60)

    try:
        ctx = await resolve_rbac_context(company_id, employee_id, engine)

        print(f"\n[OK] RBAC Context Resolved Successfully!")
        print(f"  Company ID:        {ctx.company_id}")
        print(f"  Employee ID:       {ctx.employee_id}")
        print(f"  Roles:             {ctx.role_names}")
        print(f"  Scope Type:        {ctx.scope_type.value}")
        print(f"  Can View Salary:   {ctx.can_view_salary}")
        print(f"  Accessible Employees: {len(ctx.accessible_employee_ids)} IDs")
        if ctx.accessible_employee_ids:
            preview = ctx.accessible_employee_ids[:15]
            print(f"  Sample IDs:        {preview}")
        print(f"  Accessible Depts:  {len(ctx.accessible_department_ids)} IDs")
        if ctx.accessible_department_ids:
            preview = ctx.accessible_department_ids[:10]
            print(f"  Sample Dept IDs:   {preview}")

    except Exception as e:
        print(f"\n[FAIL] RBAC resolution FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
