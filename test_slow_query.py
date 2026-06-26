import asyncio
import time
from sqlalchemy import create_engine, text, event
from module.utils import config
import urllib.parse

def test_query():
    db_creds = config["production"]["chatbot_db_credentials"]
    _encoded_password = urllib.parse.quote_plus(str(db_creds['password']))
    _port = int(db_creds['port'])

    uri = (
        f"mysql+mysqlconnector://{db_creds['user']}:{_encoded_password}"
        f"@{db_creds['host']}:{_port}/"
    )
    print("Connecting...")
    engine = create_engine(uri)
    
    @event.listens_for(engine, "connect")
    def set_max_execution_time(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("SET SESSION MAX_EXECUTION_TIME=5000") # 5 seconds
        cursor.close()

    query = "SELECT latestClockOutTime FROM `hcmatrix-time-and-attendance-db`.`v_employee_latest_clock` WHERE companyId = 1 AND employeeId = 1221;"
    print(f"Executing: {query}")
    
    start = time.time()
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query)).fetchall()
            print(f"Result: {result}")
    except Exception as e:
        print(f"Error: {type(e).__name__} - {e}")
    print(f"Time taken: {time.time() - start:.2f}s")

if __name__ == "__main__":
    test_query()
