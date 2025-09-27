import os
from dotenv import load_dotenv

# Carrega .env do diretório raiz
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# ID do coletor
ID_COLLECTOR = os.getenv("ID_COLLECTOR", "default")

# Configuração SQLite
SQLITE_CONFIG = {
    "type": "sqlite",
    "path": os.getenv("DB_PATH", os.path.join(BASE_DIR, "analysis.db"))
}

# Configuração MySQL
MYSQL_CONFIG = {
    "type": "mysql",
    "host": os.getenv("DB_HOST", ""),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", ""),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "")
}

# Exportar nomes
__all__ = ["ID_COLLECTOR", "SQLITE_CONFIG", "MYSQL_CONFIG"]
