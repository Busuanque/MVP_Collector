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
from dotenv import load_dotenv

from dbconfig import ID_COLLECTOR, DB_CONFIG
from uv_index import get_uv_index
from fitzpatrick import analyze_fitzpatrick
from recommendations import get_recommendations, format_analysis_html

# Carrega variáveis de ambiente
ID_COLLECTOR = os.getenv("ID_COLLECTOR", "default")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, "../.env"))


# Configurações fixas (hard-coded no main.py)
SQLITE_CONFIG = {
    "path": "scp.db"  # Caminho fixo para o arquivo SQLite
}

# Configuração do Flask
app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
app.secret_key = os.urandom(24)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection_sqlite():
    cfg = SQLITE_CONFIG
    conn = sqlite3.connect(cfg["path"], check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def get_db_connection_mysql():
    cfg = DB_CONFIG

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
            "SELECT COUNT(*) FROM analysis_log WHERE id_collector = ?",
            (ID_COLLECTOR,)
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
    recs = json.dumps(kwargs.get("recommendations", []))
    data = (
        ID_COLLECTOR, ts, event, input_type, input_val,
        session.get("location"), kwargs.get("uv_index"),
        kwargs.get("fitzpatrick_type"), recs, kwargs.get("status_message")
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
        "SELECT * FROM analysis_log WHERE id_collector = ? ORDER BY timestamp",
        (ID_COLLECTOR,)
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
#
#

@app.route("/export_db", methods=["POST"])
def export_db():

    print(f"")
    print("Iniciando export_db..")
    # 1) Ler dados do SQLite
    sqlite_path = SQLITE_CONFIG["path"]
    with sqlite3.connect(sqlite_path) as conn_s:
        cur_s = conn_s.cursor()
        # Use placeholder ? para filtro
        cur_s.execute("SELECT id, id_collector, timestamp, input_value, location, uv_index, fitzpatrick_type, recommendations, status_message FROM analysis_log")
        rows = cur_s.fetchall()

    # 2) Conectar ao MySQL e inserir cada row
    cfg = DB_CONFIG.copy()
    cfg.pop("type", None)
    conn_m = mysql.connector.connect(**cfg)
    cur_m = conn_m.cursor()

    sql_insert = """
    INSERT INTO scp.analises
      (id_colletor, data_hora, nome_imagem, localizacao,
       indice_uv, tipo_pele, recomendacoes, estado, imagem_blob)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    for row in rows:
        _, id_col, ts, img_path, loc, uv, skin, recs, status = row
        # Carregar blob
        img_blob = None
        if img_path and os.path.exists(img_path):
            with open(img_path, "rb") as f:
                img_blob = f.read()

        params = (
            id_col,
            ts,
            os.path.basename(img_path) if img_path else None,
            loc,
            uv,
            skin,
            recs,
            status,
            img_blob
        )
        cur_m.execute(sql_insert, params)

    conn_m.commit()
    cur_m.close()
    conn_m.close()

    print("export_db finalizado com sucesso.")
    return jsonify({"status": "success", "message": "Dados exportados para MySQL", "quantidade": len(rows)})

#
#
#

if __name__ == "__main__":
    print("Iniciando Flask em http://localhost:5000...")
    app.run(host="0.0.0.0", port=5000, debug=True)
