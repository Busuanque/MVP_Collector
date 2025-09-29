# src/main.py

#python
import os
import json
import time
import uuid
from datetime import datetime
from io import StringIO

from flask import Flask, render_template, request, jsonify, session, make_response
from werkzeug.utils import secure_filename
import sqlite3
import mysql.connector
from mysql.connector import Error as MySQLError

from dotenv import load_dotenv

from dbconfig import ID_COLLECTOR, DB_CONFIG
from uv_index import get_uv_index
from fitzpatrick import analyze_fitzpatrick
from recommendations import get_recommendations, format_analysis_html

# Carrega variáveis de ambiente
ID_COLLECTOR = os.getenv("ID_COLLECTOR", "default")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, "../.env"))


# Configs DB
print("DB Path:", os.path.join(BASE_DIR,"analysis.db"))
SQLITE_CONFIG = {
    "path": os.path.join(BASE_DIR,"analysis.db")
}

MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "scp_user",
    "password": "scp_user",  # Substitua pela senha real
    "database": "scp"
}

# Configuração do Flask
app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
app.secret_key = os.urandom(24)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}


analises_coletadas = []

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection_sqlite():
    cfg = SQLITE_CONFIG
    conn = sqlite3.connect(cfg["path"], check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def get_db_connection_mysql():
    cfg = MYSQL_CONFIG
    return mysql.connector.connect(
        host=cfg["host"], port=cfg["port"],
        user=cfg["user"], password=cfg["password"],
        database=cfg["database"], charset="utf8mb4"
    )

def init_db():
    """Inicializa schemas em MySQL e SQLite."""
    statuses = {}
    statuses["mysql"] = "MySQL pronto"
    statuses["sqlite"] = "SQLite pronto"

    return statuses

def log_analysis(event_type, input_type=None, input_value=None, **kwargs):
    #print("Log_analisys chamada:", event_type, input_type, input_value, kwargs)
    ts = datetime.now().isoformat()
    recs = json.dumps(kwargs.get("recommendations", []))
    data = (
        ID_COLLECTOR, ts, event_type, input_type, input_value,
        session.get("location"), kwargs.get("uv_index"),
        kwargs.get("fitzpatrick_type"), recs, kwargs.get("status_message")
    )
    # SQLite
    try:
        conn = get_db_connection_sqlite()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO analysis_log
            (id_collector,timestamp,event_type,input_type,input_value,
             location,uv_index,fitzpatrick_type,recommendations,status_message)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, data)
        conn.commit()
    except:
        pass
    finally:
        cur.close(); conn.close()

@app.route("/")
def index():
    statuses = init_db()
    session["location"] = None
    session["photo_path"] = None
    return render_template(
        "index.html",
        status_message=" | ".join(statuses.values()),
        status_color="#00B300" if all("pronto" in v.lower() for v in statuses.values()) else "#FF0000"
    )

@app.route("/detect_location", methods=["GET"])
def detect_location():
    cache = "location_cache.json"
    try:
        if os.path.exists(cache):
            with open(cache) as f:
                c = json.load(f)
            if time.time() - c["timestamp"] < 3600:
                session["location"] = c["location"]
                return jsonify(
                    status="success",
                    location=c["location"],
                    message="Localização da cache!",
                    message_color="#00B300"
                )
    except:
        pass

    try:
        key = os.getenv("IPGEOLOCATION_API_KEY")
        if not key:
            raise Exception("API key faltando")
        url = f"https://api.ipgeolocation.io/ipgeo?apiKey={key}"
        r = json.loads(__import__("requests").get(url).text)
        loc = f"{r.get('city')}, {r.get('country_name')}"
        session["location"] = loc
        with open(cache, "w") as f:
            json.dump({"location": loc, "timestamp": time.time()}, f)
        return jsonify(status="success", location=loc, message="Localização detectada!", message_color="#00B300")
    except Exception as e:
        try:
            from geopy.geocoders import Nominatim
            loc = Nominatim(user_agent="mvp").geocode("Lisbon, Portugal").address
            session["location"] = loc
            log_analysis("location_detected", "fallback", loc, status_message=str(e))
            return jsonify(status="warning", location=loc, message=f"Fallback: {e}", message_color="#FFA500")
        except Exception as ex:
            log_analysis("location_failed", None, None, status_message=str(ex))
            return jsonify(status="error", location="Unknown", message="Erro localização", message_color="#FF0000")

@app.route("/upload", methods=["POST"])
def upload_photo():
    if "photo" not in request.files:
        return jsonify(status="error", message="Nenhuma foto enviada.", message_color="#FF0000")
    f = request.files["photo"]
    if f.filename == "" or not allowed_file(f.filename):
        return jsonify(status="error", message="Tipo inválido.", message_color="#FF0000")
    fn = secure_filename(f"{uuid.uuid4()}_{f.filename}")
    path = os.path.join(app.config["UPLOAD_FOLDER"], fn)
    f.save(path)
    session["photo_path"] = path
    return jsonify(status="success", filename=fn, message="Foto carregada!", message_color="#00B300")

@app.route("/analyze", methods=["POST"])
def analyze():
    if not session.get("location"):
        return jsonify(status="error", message="Localização não detectada.", message_color="#FF0000")
    pp = session.get("photo_path")
    if not pp or not os.path.exists(pp):
        return jsonify(status="error", message="Foto não encontrada.", message_color="#FF0000")
    try:
        uv_data = get_uv_index(session["location"])
        uv_index = uv_data.get("uv", 0) if isinstance(uv_data, dict) else 0
        st = analyze_fitzpatrick(pp)
        recs = get_recommendations(uv_index, st)
        html = format_analysis_html(uv_index, st, recs)
        log_analysis("analysis_completed", "photo+location", pp, uv_index=uv_index, fitzpatrick_type=st, recommendations=recs)
        session["uv_index"] = uv_index
        session["skin_type"] = st
        return jsonify(status="success", result_html=html, message="Análise concluída!", message_color="#00B300")
    except Exception as e:
        log_analysis("analysis_failed", None, None, status_message=str(e))
        return jsonify(status="error", message=f"Erro na análise: {e}", message_color="#FF0000")

@app.route("/count_analyses", methods=["GET"])
def count_analyses():
    """
    Retorna o total de registros no SQLite para este ID_COLLECTOR.
    """
    try:
        conn = get_db_connection_sqlite()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM analysis_log"
        )
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return jsonify(status="success", count=count)
    except Exception as e:
        return jsonify(status="error", message=str(e), count=0)

# Alias para /export
@app.route("/export", methods=["GET"])
def export_alias():
    return export_csv()



def log_sqlite(event, input_type=None, input_val=None, **kwargs):
    """Grava apenas no SQLite."""
    conn = get_db_connection_sqlite()
    cur = conn.cursor()
    ts = datetime.now().isoformat()

    #recs = json.dumps(kwargs.get("recommendations", []))
    # Usar ensure_ascii=True para converter Unicode
    recs = json.dumps(kwargs.get("recommendations", []), ensure_ascii=True)

    # Limpar status_message
    status_message = kwargs.get("status_message", "")
    if status_message:
        # Remove caracteres não-ASCII
        status_message = status_message.encode('ascii', 'ignore').decode('ascii')
        status_message = ' '.join(status_message.split())  # Remove espaços extras

    data = (
        ID_COLLECTOR, ts, event, input_type, input_val,
        session.get("location"), kwargs.get("uv_index"),
        kwargs.get("fitzpatrick_type"), recs, status_message
    )
    cur.execute("""
        INSERT INTO analysis_log
        (id_collector,timestamp,event_type,input_type,input_value,
         location,uv_index,fitzpatrick_type,recommendations,status_message)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, data)
    conn.commit()
    cur.close()
    conn.close()

@app.route("/export_csv", methods=["GET"])
def export_csv():
    import csv
    """Lê do SQLite e gera CSV."""
    conn = get_db_connection_sqlite()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM analysis_log"
    )
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(cols)
    writer.writerows(rows)
    csv_data = output.getvalue()

    cur.close()
    conn.close()

    response = make_response(csv_data)
    response.headers["Content-Disposition"] = f"attachment; filename=analysis_{ID_COLLECTOR}.csv"
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    return response

#
# -------------------------------------------------------------------------------------------------------------------------------------
#
@app.route("/export_db", methods=["POST"])
def export_db():
    sqlite_conn = None
    mysql_conn = None
    sqlite_cursor = None
    mysql_cursor = None

    try:
        # 1. Conectar ao SQLite e ler registros
        sqlite_conn = get_db_connection_sqlite()
        sqlite_cursor = sqlite_conn.cursor()
        
        # Selecionar campos específicos na ordem correta
        sqlite_cursor.execute("""
            SELECT id_collector, id, timestamp, event_type, input_type, 
                   input_value, location, uv_index, fitzpatrick_type, 
                   recommendations, status_message
            FROM analysis_log
        """)
        records = sqlite_cursor.fetchall()

        if not records:
            print("Nenhum registro encontrado no SQLite")
            return jsonify({
                "status": "warning",
                "message": "Nenhum registro encontrado no SQLite",
                "transferred": 0
            }), 200

        print(f"Encontrados {len(records)} registros no SQLite")

        # 2. Conectar ao MySQL
        print("Conectando ao MySQL...")
        mysql_conn = get_db_connection_mysql()
        mysql_cursor = mysql_conn.cursor()
        print("Conectado ao MySQL com sucesso")

        # 3. Processar e inserir cada registro
        transferred_count = 0
        
        for record in records:
            # Mapeamento dos campos conforme especificado
            id_collector = record[0]        # analysis_log.id_collector
            timestamp = record[2]           # analysis_log.timestamp  
            input_value = record[5]         # analysis_log.input_value (nome_imagem)
            location = record[6]            # analysis_log.location
            uv_index = record[7]            # analysis_log.uv_index
            fitzpatrick_type = record[8]    # analysis_log.fitzpatrick_type
            recommendations = record[9]     # analysis_log.recommendations
            status_message = record[10]     # analysis_log.status_message

            # Preparar imagem_blob (path + nome da imagem)
            imagem_blob = None
            if input_value:
                # Assumindo que você tem uma variável path_imagens definida
                # path_imagens = "/caminho/para/uploads/"  # Defina conforme necessário
                # imagem_blob = path_imagens + input_value
                imagem_blob = input_value  # Por enquanto, usar apenas o nome

            # Debug: mostrar dados que serão inseridos
            print(f"\nInserindo registro {transferred_count + 1}:")
            print(f"  id_colletor: {id_collector}")
            print(f"  data_hora: {timestamp}")
            print(f"  nome_imagem: {input_value}")
            print(f"  localizacao: {location}")
            print(f"  indice_uv: {uv_index}")
            print(f"  tipo_pele: {fitzpatrick_type}")
            print(f"  recomendacoes: {recommendations}")
            print(f"  estado: {status_message}")
            print(f"  imagem_blob: {imagem_blob}")

            # Inserir no MySQL (id é auto-incremental, não precisa ser especificado)
            mysql_cursor.execute("""
                INSERT INTO scp.analises 
                (id_colletor, data_hora, nome_imagem, localizacao, 
                 indice_uv, tipo_pele, recomendacoes, estado, imagem_blob)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                id_collector,     # analises.id_colletor
                timestamp,        # analises.data_hora
                input_value,      # analises.nome_imagem
                location,         # analises.localizacao
                uv_index,         # analises.indice_uv
                fitzpatrick_type, # analises.tipo_pele
                recommendations,  # analises.recomendacoes
                status_message,   # analises.estado
                imagem_blob       # analises.imagem_blob
            ))
            
            transferred_count += 1

        # 4. Confirmar transação MySQL
        mysql_conn.commit()
        print(f"Transferidos {transferred_count} registros para MySQL com sucesso")

        # 5. Opcional: limpar SQLite após sucesso
        # sqlite_cursor.execute("DELETE FROM analysis_log")
        # sqlite_conn.commit()
        # print("Registros removidos do SQLite")

        return jsonify({
            "status": "success",
            "message": f"{transferred_count} registros transferidos com sucesso",
            "transferred": transferred_count
        }), 200

    except sqlite3.Error as sqlite_err:
        print(f"Erro no SQLite: {sqlite_err}")
        if sqlite_conn:
            sqlite_conn.rollback()
        return jsonify({
            "status": "error",
            "message": f"Erro no SQLite: {sqlite_err}",
            "transferred": 0
        }), 500

    except MySQLError as mysql_err:
        print(f"Erro no MySQL: {mysql_err}")
        if mysql_conn:
            mysql_conn.rollback()
        return jsonify({
            "status": "error",
            "message": f"Erro no MySQL: {mysql_err}",
            "transferred": 0
        }), 500

    except Exception as e:
        print(f"Erro geral: {e}")
        if mysql_conn:
            mysql_conn.rollback()
        if sqlite_conn:
            sqlite_conn.rollback()
        return jsonify({
            "status": "error",
            "message": f"Erro geral: {e}",
            "transferred": 0
        }), 500

    finally:
        # Fechar conexões
        if sqlite_cursor:
            sqlite_cursor.close()
        if mysql_cursor:
            mysql_cursor.close()
        if mysql_conn and mysql_conn.is_connected():
            mysql_conn.close()
        if sqlite_conn:
            sqlite_conn.close()
            
            
# -------------------------------------------------------------------------------------------------------------------------------------
# 


if __name__ == "__main__":
    print("Iniciando Flask em http://localhost:5000...")
    app.run(host="0.0.0.0", port=5000, debug=True)
