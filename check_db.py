"""Quick script to list all tables and views in the connected database."""
import os
from dotenv import load_dotenv
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text

load_dotenv()

from module.utils import config

db_creds = config["production"]["chatbot_db_credentials"]
_encoded_password = quote_plus(str(db_creds['password']))
_port = int(db_creds['port'])
uri = f"mysql+mysqlconnector://{db_creds['user']}:{_encoded_password}@{db_creds['host']}:{_port}/{db_creds['database']}"

print(f"Connecting to: {db_creds['host']}:{_port}/{db_creds['database']}")

engine = create_engine(uri)
with engine.connect() as conn:
    result = conn.execute(text("SHOW FULL TABLES"))
    rows = result.fetchall()
    print(f"\nFound {len(rows)} tables/views in '{db_creds['database']}':\n")
    for row in rows:
        name, table_type = row
        label = "[VIEW]" if table_type == "VIEW" else "[TABLE]"
        print(f"  {label} {name}")
