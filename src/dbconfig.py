import os
from dotenv import load_dotenv

load_dotenv()

ID_COLLECTOR = os.getenv("ID_COLLECTOR", "default")

DB_TYPE = os.getenv("DB_TYPE", "sqlite")

if DB_TYPE == "mysql":
    DB_CONFIG = {
        "type": "mysql",
        "host": os.getenv("DB_HOST", "127.0.0.1"),  # IP ou hostname para export distribuído
        "port": int(os.getenv("DB_PORT", 3306)),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "database": os.getenv("DB_NAME")
    }
    if not all([DB_CONFIG["user"], DB_CONFIG["password"], DB_CONFIG["database"]]):
        raise ValueError("DB_USER, DB_PASSWORD, and DB_NAME must be set for MySQL in .env")
else:
    DB_CONFIG = {
        "type": "sqlite",
        "path": os.getenv("DB_PATH", "analysis.db")
    }

if DB_TYPE == "mysql" and not DB_CONFIG["host"]:
    raise ValueError("DB_HOST must be set for MySQL in .env")