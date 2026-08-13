import sys
import os
from sqlalchemy import create_engine, text
sys.path.insert(0, os.path.dirname(os.path.abspath('test_rbac_sp.py')))
from module.utils import config
from urllib.parse import quote_plus
db_creds = config['production']['chatbot_db_credentials']
uri = f"mysql+mysqlconnector://{db_creds['user']}:{quote_plus(str(db_creds['password']))}@{db_creds['host']}:{int(db_creds['port'])}/hcmatrix-utility-db"
engine = create_engine(uri)
with engine.connect() as conn:
    res = conn.execute(text('SHOW CREATE PROCEDURE sp_accessible_employees')).fetchone()
    print(res[2])
