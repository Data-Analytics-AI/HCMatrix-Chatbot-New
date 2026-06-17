import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
from module.utils import config

chatbot_db_credentials = config['production']['chatbot_db_credentials']
uri = f"mysql+mysqlconnector://{chatbot_db_credentials['user']}:{chatbot_db_credentials['password']}@{chatbot_db_credentials['host']}:{chatbot_db_credentials['port']}/{chatbot_db_credentials['database']}"

engine = create_engine(uri)
with engine.connect() as conn:
    res = conn.execute(text("SELECT hospitalName FROM v_employee_hmo_hospitals WHERE employeeId = 1221"))
    rows = res.fetchall()
    print("Number of hospitals for 1221:", len(rows))
    print("Rows:", rows)
