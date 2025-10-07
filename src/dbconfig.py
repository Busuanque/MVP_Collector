import os
from dotenv import load_dotenv

# ID do coletor
ID_COLLECTOR = os.getenv("ID_COLLECTOR", "default")

MYSQL_CONFIG = {
    'host': 'localhost',
    'database': 'scp',
    'user': 'scp_user',
    'password': 'scp_user',  # Substitua pela senha real
    'port': 3306
}
