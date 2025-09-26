from flask import Flask, render_template, request, jsonify, session
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from dbconfig import DB_CONFIG, ID_COLLECTOR
import os
import json
import time
from datetime import datetime
import uuid
import requests
import csv
from io import StringIO
from flask import make_response
import mysql.connector
import sqlite3

# Import modules (assume created)
from uv_index import get_uv_index
from fitzpatrick import analyze_fitzpatrick
from recommendations import get_recommendations

load_dotenv()
analises_coletadas = []  # Lista temporária para dados de análises

app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.config["UPLOAD_FOLDER"] = os.getenv("UPLOAD_FOLDER", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size
app.secret_key = os.urandom(24)  # For session management
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    """Initialize or update database schema with id_collector support (MySQL preservado)."""
    try:
        if DB_CONFIG["type"] == "mysql":
            conn = mysql.connector.connect(**{k: v for k, v in DB_CONFIG.items() if k != "type"})
            cursor = conn.cursor()
            # Check if table exists
            cursor.execute("SHOW TABLES LIKE 'analysis_log'")
            table_exists = cursor.fetchone()
            if not table_exists:
                # Create new table
                cursor.execute("""
                    CREATE TABLE analysis_log (
                        id_collector VARCHAR(255),
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        timestamp DATETIME NOT NULL,
                        event_type VARCHAR(255) NOT NULL,
                        input_type VARCHAR(255),
                        input_value TEXT,
                        location TEXT,
                        uv_index DECIMAL(3,1),
                        fitzpatrick_type VARCHAR(10),
                        recommendations TEXT,
                        status_message TEXT
                    )
                """)
                conn.commit()
                return {"status": "success", "message": "Banco MySQL criado com id_collector!"}
            
            # Check column
            cursor.execute("DESCRIBE analysis_log")
            columns = [col[0] for col in cursor.fetchall()]
            if "id_collector" not in columns:
                cursor.execute("ALTER TABLE analysis_log ADD COLUMN id_collector VARCHAR(255) FIRST")
                cursor.execute("UPDATE analysis_log SET id_collector = %s WHERE id_collector IS NULL", (ID_COLLECTOR,))
                conn.commit()
                return {"status": "success", "message": "Banco MySQL migrado com id_collector!"}
            return {"status": "success", "message": "Banco MySQL pronto com id_collector!"}
        else:
            import sqlite3
            with sqlite3.connect(DB_CONFIG["path"]) as conn:
                cursor = conn.cursor()
                # Check if table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='analysis_log'")
                table_exists = cursor.fetchone()
                if not table_exists:
                    # Create new table
                    cursor.execute("""
                        CREATE TABLE analysis_log (
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
                    return {"status": "success", "message": "Banco SQLite criado com id_collector!"}
                
                # Check column
                cursor.execute("PRAGMA table_info(analysis_log)")
                columns = [col[1] for col in cursor.fetchall()]
                if "id_collector" not in columns:
                    cursor.execute("ALTER TABLE analysis_log ADD COLUMN id_collector TEXT")
                    cursor.execute("UPDATE analysis_log SET id_collector = ? WHERE id_collector IS NULL", (ID_COLLECTOR,))
                    conn.commit()
                    return {"status": "success", "message": "Banco SQLite migrado com id_collector!"}
                return {"status": "success", "message": "Banco SQLite pronto com id_collector!"}
    except Exception as e:
        return {"status": "error", "message": f"Erro no banco: {str(e)}"}

def log_analysis(event_type, input_type=None, input_value=None, **kwargs):
    """Log analysis events to DB with id_collector (MySQL preservado)."""
    try:
        if DB_CONFIG["type"] == "mysql":
            conn = mysql.connector.connect(**{k: v for k, v in DB_CONFIG.items() if k != "type"})
            cursor = conn.cursor()
            timestamp = datetime.now()
            cursor.execute("""
                INSERT INTO analysis_log 
                (id_collector, timestamp, event_type, input_type, input_value, location, uv_index, fitzpatrick_type, recommendations, status_message)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                ID_COLLECTOR, timestamp, event_type, input_type, input_value,
                session.get("location"), kwargs.get("uv_index"), kwargs.get("fitzpatrick_type"),
                json.dumps(kwargs.get("recommendations", [])), kwargs.get("status_message")
            ))
            conn.commit()
            cursor.close()
            conn.close()
        else:
            import sqlite3
            with sqlite3.connect(DB_CONFIG["path"]) as conn:
                cursor = conn.cursor()
                timestamp = datetime.now().isoformat()
                cursor.execute("""
                    INSERT INTO analysis_log 
                    (id_collector, timestamp, event_type, input_type, input_value, location, uv_index, fitzpatrick_type, recommendations, status_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ID_COLLECTOR, timestamp, event_type, input_type, input_value,
                    session.get("location"), kwargs.get("uv_index"), kwargs.get("fitzpatrick_type"),
                    json.dumps(kwargs.get("recommendations", [])), kwargs.get("status_message")
                ))
                conn.commit()
    except Exception as e:
        print(f"Log error: {e}")

@app.route("/")
def index():
    """Render the main page."""
    db_result = init_db()
    session["location"] = None
    session["photo_path"] = None
    return render_template("index.html", status_message=db_result["message"],
                         status_color="#00B300" if db_result["status"] == "success" else "#FF0000")

@app.route("/detect_location", methods=["GET"])
def detect_location():
    """Detect user's location using ipgeolocation.io API with caching and geopy fallback."""
    cache_file = "location_cache.json"
    cache_duration = 3600  # 1 hour
    try:
        if os.path.exists(cache_file):
            with open(cache_file, "r") as f:
                cache_data = json.load(f)
            if time.time() - cache_data.get("timestamp", 0) < cache_duration:
                location = cache_data.get("location")
                session["location"] = location
                log_analysis("location_detected", "cache", location)
                return jsonify({
                    "status": "success",
                    "location": location,
                    "message": "Localização carregada da cache!",
                    "message_color": "#00B300"
                })
    except Exception:
        pass

    try:
        api_key = os.getenv("IPGEOLOCATION_API_KEY")
        if not api_key:
            raise Exception("IPGEOLOCATION_API_KEY não encontrado no ficheiro .env.")
        url = f"https://api.ipgeolocation.io/ipgeo?apiKey={api_key}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            location = f"{data.get('city', 'Unknown')}, {data.get('country_name', 'Unknown')}"
            session["location"] = location
            # Cache it
            cache_data = {"location": location, "timestamp": time.time()}
            with open(cache_file, "w") as f:
                json.dump(cache_data, f)
            # Log to DB
            log_analysis("location_detected", "api", location)
            return jsonify({
                "status": "success",
                "location": location,
                "message": "Localização detectada!",
                "message_color": "#00B300"
            })
        else:
            raise Exception(f"API error: {response.status_code}")
    except Exception as e:
        # Fallback to geopy
        try:
            from geopy.geocoders import Nominatim
            geolocator = Nominatim(user_agent="mvp_collector")
            # Default fallback; in production, use user-provided coords
            location = geolocator.geocode("Lisbon, Portugal").address if geolocator else "Unknown"
            session["location"] = location
            log_analysis("location_detected", "fallback", location, status_message=str(e))
            return jsonify({
                "status": "warning",
                "location": location,
                "message": f"Fallback usado: {str(e)}",
                "message_color": "#FFA500"
            })
        except Exception as fallback_e:
            log_analysis("location_detected", None, None, status_message=str(fallback_e))
            return jsonify({
                "status": "error",
                "location": "Unknown",
                "message": f"Erro na detecção: {str(fallback_e)}",
                "message_color": "#FF0000"
            })

@app.route("/upload", methods=["POST"])
def upload_photo():
    """Handle photo upload and save securely."""
    if "photo" not in request.files:
        return jsonify({"status": "error", "message": "Nenhuma foto enviada.", "message_color": "#FF0000"})
    
    file = request.files["photo"]
    if file.filename == "":
        return jsonify({"status": "error", "message": "Nenhum ficheiro selecionado.", "message_color": "#FF0000"})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)
        session["photo_path"] = filepath
        log_analysis("photo_uploaded", "file", filename)
        return jsonify({
            "status": "success",
            "filename": filename,
            "message": "Foto carregada com sucesso!",
            "message_color": "#00B300"
        })
    else:
        return jsonify({"status": "error", "message": "Tipo de ficheiro não permitido.", "message_color": "#FF0000"})

@app.route("/analyze", methods=["POST"])
def analyze():
    """Analyze photo for Fitzpatrick type and get UV index."""
    if not session.get("location"):
        return jsonify({"status": "error", "message": "Localização não detectada. Detete primeiro.", "message_color": "#FF0000"})
    
    photo_path = session.get("photo_path")
    if not photo_path or not os.path.exists(photo_path):
        return jsonify({"status": "error", "message": "Foto não encontrada.", "message_color": "#FF0000"})
    
    try:
        # Get UV
        uv_data = get_uv_index(session["location"])
        uv_index = uv_data.get("uv", 0) if uv_data else 0
        
        # Analyze skin
        skin_type = analyze_fitzpatrick(photo_path)
        
        # Log
        log_analysis("analysis_completed", "photo+location", photo_path, uv_index=uv_index, fitzpatrick_type=skin_type)
        
        session["uv_index"] = uv_index
        session["skin_type"] = skin_type
        
        return jsonify({
            "status": "success",
            "uv_index": uv_index,
            "skin_type": skin_type,
            "message": "Análise concluída!",
            "message_color": "#00B300"
        })
    except Exception as e:
        log_analysis("analysis_failed", None, None, status_message=str(e))
        return jsonify({
            "status": "error",
            "message": f"Erro na análise: {str(e)}",
            "message_color": "#FF0000"
        })

@app.route("/recommend", methods=["GET"])
def recommend():
    """Get personalized recommendations."""
    location = session.get("location")
    uv_index = session.get("uv_index", 0)
    skin_type = session.get("skin_type")
    
    if not all([location, uv_index, skin_type]):
        return jsonify({"status": "error", "message": "Análise incompleta. Analise primeiro.", "message_color": "#FF0000"})
    
    recs = get_recommendations(uv_index, skin_type)
    log_analysis("recommendations_generated", "uv+skin", f"{uv_index}-{skin_type}", recommendations=recs)
    
    return jsonify({
        "status": "success",
        "recommendations": recs,
        "message": "Recomendações geradas!",
        "message_color": "#00B300"
    })

@app.route("/export", methods=["GET"])
def export_csv():
    """Export logs as CSV for this id_collector (preserva MySQL query)."""
    try:
        if DB_CONFIG["type"] == "mysql":
            conn = mysql.connector.connect(**{k: v for k, v in DB_CONFIG.items() if k != "type"})
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM analysis_log WHERE id_collector = %s ORDER BY timestamp", (ID_COLLECTOR,))
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            cursor.close()
            conn.close()
        else:
            import sqlite3
            with sqlite3.connect(DB_CONFIG["path"]) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM analysis_log WHERE id_collector = ? ORDER BY timestamp", (ID_COLLECTOR,))
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
        
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(columns)
        writer.writerows(rows)
        
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = f"attachment; filename=analysis_{ID_COLLECTOR}.csv"
        response.headers["Content-type"] = "text/csv"
        return response
    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro no export: {str(e)}", "message_color": "#FF0000"})


#
# 
# 
# 
# 

@app.route("/count_analyses", methods=["GET"])
def count_analyses():
    """Rota para contar análises no DB (corrige 404 no JS)."""
    try:
        if DB_CONFIG["type"] == "mysql":
            conn = mysql.connector.connect(**{k: v for k, v in DB_CONFIG.items() if k != "type"})
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM analysis_log WHERE id_collector = %s", (ID_COLLECTOR,))
            count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
        else:
            with sqlite3.connect(DB_CONFIG["path"]) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM analysis_log WHERE id_collector = ?", (ID_COLLECTOR,))
                count = cursor.fetchone()[0]
        
        return jsonify({"status": "success", "count": count})
    except Exception as e:
        print(f"Count error: {e}")
        return jsonify({"status": "error", "message": str(e), "count": 0})



# ========== Flask standalone for Windows ===================================
if __name__ == '__main__':
    print("Iniciando Flask em http://localhost:5000...")  # Para debug
    app.run(host='0.0.0.0', port=5000, debug=True)