from flask import Flask, render_template, request, jsonify, session
from werkzeug.utils import secure_filename
from uv_index import get_uv_index
from fitzpatrick import analyze_fitzpatrick
from recommendations import get_recommendations
from dotenv import load_dotenv
import os
import json
import time
import sqlite3
from datetime import datetime
import base64
import io
from PIL import Image
import requests
# database
import mysql.connector
from mysql.connector import Error
from config import DB_CONFIG  # Novo import

app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.config["UPLOAD_FOLDER"] = "Uploads"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size
app.secret_key = os.urandom(24)  # For session management
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Load environment variables
load_dotenv()

def init_db():
    """Initialize or update SQLite database schema."""
    try:
        with sqlite3.connect("analysis.db") as conn:
            cursor = conn.cursor()
            # Check existing table schema
            cursor.execute("PRAGMA table_info(analysis_log)")
            columns = [col[1] for col in cursor.fetchall()]
            required_columns = [
                "id", "timestamp", "event_type", "input_type", "input_value",
                "location", "uv_index", "fitzpatrick_type", "recommendations", "status_message"
            ]
            
            if not all(col in columns for col in required_columns):
                # If schema is missing columns, rename existing table
                if columns:  # Table exists
                    cursor.execute("ALTER TABLE analysis_log RENAME TO analysis_log_old")
                # Create new table with correct schema
                cursor.execute("""
                    CREATE TABLE analysis_log (
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
                # Migrate data if old table exists (only ANALYSIS events)
                if columns:
                    common_columns = [col for col in columns if col in required_columns]
                    if common_columns and "event_type" in columns:
                        columns_str = ", ".join(common_columns)
                        cursor.execute(f"""
                            INSERT INTO analysis_log ({columns_str})
                            SELECT {columns_str} FROM analysis_log_old WHERE event_type = 'ANALYSIS'
                        """)
                    cursor.execute("DROP TABLE analysis_log_old")
                conn.commit()
        return {"status": "success", "message": "Base de dados pronta!"}
    except sqlite3.Error as e:
        return {"status": "error", "message": f"Erro na base de dados: {str(e)}"}

def insert_to_db(analise_data):
    """
    Nova função: Insere um dict de análise diretamente no DB (tabela analises_pele).
    Não afeta o export CSV. Exemplo analise_data: dict com chaves da tabela.
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO analises_pele (id_colletor, data_hora, nome_imagem, localizacao, indice_uv, tipo_pele, recomendacoes, estado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            analise_data['id_colletor'],
            analise_data['data_hora'],
            analise_data['nome_imagem'],
            analise_data['localizacao'],
            analise_data['indice_uv'],
            analise_data['tipo_pele'],
            analise_data['recomendacoes'],
            analise_data.get('estado', 'Análise concluída com sucesso')  # Default se não passado
        ))
        conn.commit()
        print(f"Dados inseridos no DB com ID: {cursor.lastrowid}")  # ID auto gerado
    except Error as e:
        print(f"Erro ao inserir no DB: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn.is_connected():
            conn.close()

@app.route('/save_to_db', methods=['POST'])  # Nova rota: POST para batch de analises
def save_batch_to_db():
    if not analises:  # Assuma lista global/temporária existente
        return jsonify({'erro': 'Nenhum dado para inserir'}), 400
    
    for data in analises:
        insert_to_db(data)  # Chama a nova função para cada item
    
    # Opcional: Limpe a lista após insert (não afeta CSV)
    analises.clear()
    
    return jsonify({'status': 'Dados inseridos no DB', 'quantidade': len(analises)}), 200

@app.route("/")
def index():
    """Render the main page."""
    db_result = init_db()
    session["location"] = None
    session["photo_path"] = None
    return render_template("index.html", status_message=db_result["message"], status_color="#00B300" if db_result["status"] == "success" else "#FF0000")

@app.route("/detect_location", methods=["GET"])
def detect_location():
    """Detect user's location using ipgeolocation.io API with caching."""
    cache_file = "location_cache.json"
    cache_duration = 3600  # 1 hour

    try:
        if os.path.exists(cache_file):
            with open(cache_file, "r") as f:
                cache_data = json.load(f)
            if time.time() - cache_data.get("timestamp", 0) < cache_duration:
                location = cache_data.get("location")
                session["location"] = location
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
        response = requests.get(url, timeout=10)
        if response.status_code == 401:
            raise Exception("Chave API inválida ou não autorizada.")
        elif response.status_code == 429:
            raise Exception("Limite de pedidos da API excedido.")
        response.raise_for_status()
        data = response.json()
        city = data.get("city", "Desconhecido")
        country = data.get("country_name", "Desconhecido")
        if city == "Desconhecido" or country == "Desconhecido":
            raise Exception("Dados de localização inválidos.")
        location = f"{city}, {country}"
        session["location"] = location
        try:
            with open(cache_file, "w") as f:
                json.dump({"location": location, "timestamp": time.time()}, f)
        except Exception:
            pass
        return jsonify({
            "status": "success",
            "location": location,
            "message": "Localização detetada com sucesso!",
            "message_color": "#00B300"
        })
    except Exception as e:
        session["location"] = None
        return jsonify({
            "status": "error",
            "location": "Falha na deteção da localização.",
            "message": f"Erro: {str(e)}",
            "message_color": "#FF0000"
        })

@app.route("/upload_photo", methods=["POST"])
def upload_photo():
    """Handle photo upload from file or camera."""
    if "photo" in request.files and request.files["photo"].filename:
        file = request.files["photo"]
        if file.filename.lower().endswith((".jpg", ".png")):
            filename = secure_filename(file.filename)
            photo_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(photo_path)
            session["photo_path"] = photo_path
            return jsonify({
                "status": "success",
                "photo_path": photo_path,
                "message": "Foto carregada com sucesso!",
                "message_color": "#00B300"
            })
        return jsonify({
            "status": "error",
            "message": "Formato de arquivo inválido. Use JPG ou PNG.",
            "message_color": "#FF0000"
        })
    elif "photo_data" in request.form:
        try:
            # Handle base64-encoded image from camera
            photo_data = request.form["photo_data"]
            # Remove data URL prefix (e.g., "data:image/jpeg;base64,")
            if "," in photo_data:
                photo_data = photo_data.split(",")[1]
            image_data = base64.b64decode(photo_data)
            image = Image.open(io.BytesIO(image_data))
            # Ensure image is in JPEG format
            filename = f"camera_{int(time.time())}.jpg"
            photo_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            image.save(photo_path, "JPEG")
            session["photo_path"] = photo_path
            return jsonify({
                "status": "success",
                "photo_path": photo_path,
                "message": "Foto capturada com sucesso!",
                "message_color": "#00B300"
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Erro ao processar foto capturada: {str(e)}",
                "message_color": "#FF0000"
            })
    return jsonify({
        "status": "error",
        "message": "Nenhuma foto selecionada ou capturada.",
        "message_color": "#FF0000"
    })

@app.route("/analyze", methods=["POST"])
def analyze():
    """Analyze UV index, Fitzpatrick type, provide recommendations, and log to database."""
    data = request.get_json()
    location = data.get("location") or session.get("location")
    photo_path = data.get("photo_path") or session.get("photo_path")

    if not location:
        return jsonify({
            "status": "error",
            "message": "Localização não detetada. Tente novamente.",
            "message_color": "#FF0000"
        })
    if not photo_path or not os.path.exists(photo_path):
        return jsonify({
            "status": "error",
            "message": "Por favor, carregue ou capture uma foto da sua mão.",
            "message_color": "#FF0000"
        })

    try:
        uv_index = get_uv_index(location)
        fitzpatrick_type = analyze_fitzpatrick(photo_path)
        recommendations = get_recommendations(fitzpatrick_type, uv_index)

        result_text = (
            f"<b>Localização:</b> {location}<br>"
            f"<b>Índice UV:</b> {uv_index:.1f}<br>"
            f"<b>Tipo de Pele:</b> {fitzpatrick_type}<br>"
            f"<b>Dicas:</b><br>{recommendations}"
        )

        try:
            with sqlite3.connect("analysis.db") as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO analysis_log (
                        timestamp, event_type, input_type, input_value,
                        location, uv_index, fitzpatrick_type, recommendations, status_message
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "ANALYSIS",
                    "PHOTO_PATH",
                    photo_path,
                    location,
                    uv_index,
                    fitzpatrick_type,
                    recommendations,
                    "Análise concluída com sucesso"
                ))
                conn.commit()
            # Clear session data after successful analysis
            session["photo_path"] = None
            return jsonify({
                "status": "success",
                "result": result_text,
                "message": "Análise concluída e guardada!",
                "message_color": "#00B300"
            })
        except sqlite3.Error as e:
            return jsonify({
                "status": "error",
                "message": f"Erro na base de dados: {str(e)}",
                "message_color": "#FF0000"
            })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Falha na análise: {str(e)}",
            "message_color": "#FF0000"
        })

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)