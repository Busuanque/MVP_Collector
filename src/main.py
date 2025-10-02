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

from dbconfig import ID_COLLECTOR
from uv_index import get_uv_index
from fitzpatrick import analyze_fitzpatrick
from recommendations import get_recommendations, format_analysis_html

import sys

# Carrega variáveis de ambiente
ID_COLLECTOR = os.getenv("ID_COLLECTOR", "default")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BASE_DIR, "../.env"))


# Configs DB
#print("----->DB Path:", os.path.join(BASE_DIR,"analysis.db"))
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

# Função para obter caminho correto para recursos
def get_resource_path(relative_path):
    """Obtém o caminho correto para recursos, seja em desenvolvimento ou executável"""
    try:
        # PyInstaller cria uma pasta temporária e armazena o caminho em _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def create_flask_app():
    """Cria a aplicação Flask com caminhos corretos"""
    if getattr(sys, 'frozen', False):
        # Executando como executável PyInstaller
        template_dir = get_resource_path('templates')
        static_dir = get_resource_path('static')
    else:
        # Executando em desenvolvimento
        template_dir = os.path.join(os.path.dirname(__file__), '../templates')
        static_dir = os.path.join(os.path.dirname(__file__), '../static')
    
    return Flask(__name__, 
                template_folder=template_dir, 
                static_folder=static_dir)

# Configuração do Flask
#app = Flask(__name__, template_folder="../templates", static_folder="../static")
app = create_flask_app()

# Criar pastas se não existirem
app.config["UPLOAD_FOLDER"] = "uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
app.config["EXPORT_FOLDER"] = "exports"
os.makedirs(app.config["EXPORT_FOLDER"], exist_ok=True)

app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
app.secret_key = os.urandom(24)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

analises_coletadas = []

def ensure_sqlite_table():
    """Garante que a tabela analysis_log existe no SQLite"""
    db_path = SQLITE_CONFIG["path"]
    
    # Cria diretório se não existir
    os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else '.', exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis_log (
            id_collector TEXT,
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            event_type TEXT NOT NULL,
            input_type TEXT,
            input_value TEXT,
            location TEXT,
            uv_index REAL,
            fitzpatrick_type TEXT,
            recommendations TEXT,
            status_message TEXT
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

  
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

import re
def clean_text(text):
    # Remove escapes como \uXXXX
    text = text.encode('utf-8').decode('unicode_escape')

    # Remove emojis e símbolos Unicode
    text = re.sub(r'^\[|\]$', '', text)  # Remove colchetes
    text = re.sub(r'\\u[0-9a-fA-F]{4}', '', str(text))
    text = re.sub(r'[\x00-\x1F\x7F-\x9F]', ' ', text)  # Remove caracteres de controle
    text = re.sub(r'\\[nrt"\\]', ' ', text)  # Remove barras invertidas comuns
    text = re.sub(r'\s+', ' ', text)  # Remove espaços extras
    text = re.sub(r'[^\x20-\x7E]', ' ', text)  # Remove caracteres não-ASCII

    return text.strip()

def log_analysis(event_type, input_type=None, input_value=None, **kwargs):

    ensure_sqlite_table()  # Garante que a tabela existe

    #print("Log_analisys chamada:", event_type, input_type, input_value, kwargs)
    ts = datetime.now().isoformat()
    
    # Limpa cada recomendação antes de serializar
    raw_recs = kwargs.get("recommendations", [])
    cleaned_recs = [ clean_text(rec) for rec in raw_recs ]
    recs_json = json.dumps(cleaned_recs, ensure_ascii=False)
    print("Recomendações limpas:", recs_json)
    
    data = (
        ID_COLLECTOR, 
        ts, 
        event_type, 
        input_type, 
        input_value,
        session.get("location"), 
        kwargs.get("uv_index"),
        kwargs.get("fitzpatrick_type"), 
        recs_json, 
        kwargs.get("status_message")
    )

    conn = get_db_connection_sqlite()
    cur = conn.cursor()


    # SQLite
    try:
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
    statuses = "Databases prontos"
    session["location"] = None
    session["photo_path"] = None
    return render_template(
        "index.html",
        status_message=" | ".join(statuses),
        status_color="#00B300")

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

    # Logging
    #print("Salvando foto em:", path)
    
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
        #get_uv_index = get_uv_index(session["location"])
        st = analyze_fitzpatrick(pp)
        recs = get_recommendations(uv_index, st)
        html = format_analysis_html(uv_index, st, recs)
        log_analysis("analysis_completed", "photo+location", pp, uv_index=uv_index, fitzpatrick_type=st, recommendations=recs, status_message="Análise concluída!")
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


from io import StringIO
import uuid, os, csv
from flask import make_response

@app.route("/export_csv", methods=["GET"])
def export_csv():
    # 1. Lê do SQLite e prepara CSV em memória
    conn = get_db_connection_sqlite()
    cur = conn.cursor()
    cur.execute("SELECT * FROM analysis_log")
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    cur.close()
    conn.close()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(cols)
    writer.writerows(rows)
    csv_data = output.getvalue()

    # 2. Gera nome único e caminho completo
    unique_hash = uuid.uuid4().hex
    filename = f"{ID_COLLECTOR}_{unique_hash}.csv"
    full_path = os.path.join(app.config["EXPORT_FOLDER"], filename)
    #print("--> Salvando CSV em:", full_path)

    # 3. Grava o CSV no diretório de export
    with open(full_path, "w", encoding="utf-8", newline="") as f:
        f.write(csv_data)

    # 4. Retorna o CSV como download, usando apenas o nome do arquivo
    response = make_response(csv_data)
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
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

        # 2. Conectar ao MySQL
        #print("Conectando ao MySQL...")
        mysql_conn = get_db_connection_mysql()
        mysql_cursor = mysql_conn.cursor()
        #print("Conectado ao MySQL com sucesso")

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
                #image_path = os.path.join(app.config["UPLOAD_FOLDER"], input_value)
                #print("UPLOAD_FOLDER:", app.config["UPLOAD_FOLDER"])
                try:
                    with open(input_value, "rb") as f:
                        imagem_blob = f.read()
                except Exception as e:
                    print(f"Falha ao ler imagem: {e}")
                    imagem_blob = None

            # Debug: mostrar dados que serão inseridos
            '''
            print("----------------------------------------------------------------")
            print(f"\nInserindo registro {transferred_count + 1}:")
            print(f"  id_colletor: {id_collector}")
            print(f"  data_hora: {timestamp}")
            print(f"  nome_imagem: {input_value}")
            print(f"  localizacao: {location}")
            print(f"  indice_uv: {uv_index}")
            print(f"  tipo_pele: {fitzpatrick_type}")
            print(f"  recomendacoes: {recommendations}")
            print(f"  estado: {status_message}")
            print("----------------------------------------------------------------")
            '''

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
        print(f"--> Transferidos {transferred_count} registros para MySQL com sucesso")

        # 5. limpar SQLite após sucesso
        sqlite_cursor.execute("DELETE FROM analysis_log")
        sqlite_conn.commit()

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
        #####
            
            
# -------------------------------------------------------------------------------------------------------------------------------------
# 


if __name__ == "__main__":
    print("Iniciando Flask em http://localhost:5000...")
    app.run(host="0.0.0.0", port=5000, debug=True)
