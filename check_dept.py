import asyncio
from hcm_chatbot.sql_layer import _get_cached_engine
from sqlalchemy import text
from module.utils import config
from urllib.parse import quote_plus

db_creds = config["production"]["chatbot_db_credentials"]
_encoded_password = quote_plus(str(db_creds["password"]))
_port = int(db_creds["port"])
base_uri = f"mysql+mysqlconnector://{db_creds['user']}:{_encoded_password}@{db_creds['host']}:{_port}/"
engine = _get_cached_engine(base_uri)

with engine.connect() as conn:
    q = """
SELECT a.date AS attendanceDate, a.employeeId, a.status AS attendanceStatus, a.firstClockIn AS firstClockInTime, a.lastClockOut AS lastClockOutTime, a.workedHours
FROM `hcmatrix-time-and-attendance-db`.`v_employee_daily_attendance` a
JOIN `hcmatrix-utility-db`.`v_employee_profile` p
  ON a.companyId = p.companyId AND a.employeeId = p.employeeId
WHERE a.companyId = 1
  AND p.department = 'Sales'
  AND a.employeeId IN (116, 136, 159, 163, 171, 175, 181, 185, 191, 568, 569, 649, 657, 667, 668, 669, 1132, 1221, 1610, 1828, 1972, 3894, 118, 120, 130, 1828, 117, 175, 191, 649, 159, 171, 667, 136, 163, 669, 568, 569, 1132, 1610, 1972, 3894, 657, 668, 1221, 670, 181, 185, 158)
  AND a.date BETWEEN '2026-07-28' AND '2026-08-04'
ORDER BY a.date DESC, a.employeeId ASC;
    """
    res = conn.execute(text(q)).fetchall()
    print("AI EXACT QUERY RETURNED:", len(res), "rows")
    if res:
        print("First few rows:", res[:3])
