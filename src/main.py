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
import uuid
import requests
import csv
from io import StringIO
from flask import make_response
# database
import mysql.connector
from mysql.connector import Error
from dbconfig import DB_CONFIG  # Assuma config.py com credenciais

# Load environment variables
load_dotenv()
ID_COLLECTOR = os.getenv("ID_COLLECTOR", "default_collector")
analises_coletadas = []  # Lista temporária para dados de análises

app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.config["UPLOAD_FOLDER"] = "Uploads"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size
app.secret_key = os.urandom(24)  # For session management
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


# Init revisado com suporte a id_collector
def init_db():
    """Initialize or update SQLite database schema with id_collector support."""
    try:
        with sqlite3.connect("analysis.db") as conn:
            cursor = conn.cursor()
            
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='analysis_log'")
            table_exists = cursor.fetchone()
            
            if not table_exists:
                # Create new table with id_collector as first column
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
                return {"status": "success", "message": "Base de dados criada com id_collector!"}
            
            # Check existing table schema
            cursor.execute("PRAGMA table_info(analysis_log)")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Check if id_collector exists
            if "id_collector" not in columns:
                print("Adicionando coluna id_collector...")
                
                # Add id_collector column
                cursor.execute("ALTER TABLE analysis_log ADD COLUMN id_collector TEXT")
                
                # Update existing records with current ID_COLLECTOR
                cursor.execute("UPDATE analysis_log SET id_collector = ? WHERE id_collector IS NULL", (ID_COLLECTOR,))
                
                conn.commit()
                return {"status": "success", "message": "Base de dados migrada com id_collector!"}
            
            return {"status": "success", "message": "Base de dados pronta com id_collector!"}
            
    except sqlite3.Error as e:
        return {"status": "error", "message": f"Erro na base de dados: {str(e)}"}



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
    """Handle photo upload from file or camera with unique filenames."""
    unique_id = str(uuid.uuid4())  # Generate unique ID for the image
    if "photo" in request.files and request.files["photo"].filename:
        file = request.files["photo"]
        if file.filename.lower().endswith((".jpg", ".png")):
            # Use original extension with unique ID
            ext = os.path.splitext(file.filename)[1].lower()
            filename = f"upload_{unique_id}{ext}"
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
            # Save as JPEG with unique ID
            filename = f"camera_{unique_id}.jpg"
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
                        id_collector, timestamp, event_type, input_type, input_value,
                        location, uv_index, fitzpatrick_type, recommendations, status_message
                    )
                    VALUES (?,?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ID_COLLECTOR,
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

# Adições necessárias para main.py

# ===== IMPORTS ADICIONAIS =====
import csv
from io import StringIO
from flask import make_response
import mysql.connector
from mysql.connector import Error
from dbconfig import DB_CONFIG

# ===== FUNÇÃO: CONTADOR DE ANÁLISES =====
@app.route("/count_analyses", methods=["GET"])
def count_analyses():
    """Retorna o número de análises registradas no SQLite."""
    try:
        with sqlite3.connect("analysis.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM analysis_log WHERE event_type = 'ANALYSIS'")
            count = cursor.fetchone()[0]
        return jsonify({"status": "success", "count": count})
    except sqlite3.Error as e:
        return jsonify({"status": "error", "message": str(e)})

# ===== FUNÇÃO: EXPORT CSV =====
@app.route("/export_data", methods=["GET"])
def export_data():
    """Exporta dados do SQLite para arquivo CSV."""
    try:
        with sqlite3.connect("analysis.db") as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id_collector, id, timestamp, input_value, location, uv_index, 
                       fitzpatrick_type, recommendations, status_message
                FROM analysis_log 
                WHERE event_type = 'ANALYSIS'
                ORDER BY timestamp DESC
            """)
            
            rows = cursor.fetchall()
            
            if not rows:
                return jsonify({
                    "status": "error", 
                    "message": "Nenhum dado disponível para exportar."
                })
            
            # Criar CSV
            output = StringIO()
            writer = csv.writer(output)
            
            # Cabeçalho
            header = [
                'ID_Collector', 'ID', 'Data/Hora', 'Nome_Imagem', 'Localização', 
                'Índice_UV', 'Tipo_Pele', 'Recomendações', 'Estado'
            ]
            writer.writerow(header)
            
            # Linhas de dados
            for row in rows:
                image_name = os.path.basename(row[3]) if row[3] else "N/A"
                
                csv_row = [
                    row[0] if row[0] else ID_COLLECTOR,  # ✅ CORRIGIDO
                    row[1],  # ID
                    row[2],  # timestamp
                    image_name,  # image name
                    row[4] or "N/A",  # location
                    f"{row[5]:.1f}" if row[5] is not None else "N/A",  # UV index
                    row[6] or "N/A",  # fitzpatrick_type
                    row[7] or "N/A",  # recommendations
                    row[8] or "N/A"   # status_message
                ]
                writer.writerow(csv_row)
            
            # Resposta de download
            output.seek(0)
            response = make_response(output.getvalue())
            response.headers["Content-Type"] = "text/csv; charset=utf-8"
            response.headers["Content-Disposition"] = f"attachment; filename=analises_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            return response
            
    except sqlite3.Error as e:
        return jsonify({
            "status": "error",
            "message": f"Erro SQLite: {str(e)}"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Erro na exportação: {str(e)}"
        })

# ===== FUNÇÃO: EXPORT MYSQL =====
'''
@app.route("/export_db", methods=["POST"])
def export_db():
    """Exporta dados do SQLite para MySQL e apaga registros locais após commit no MySQL."""
    try:
        # 1. Buscar dados do SQLite
        sqlite_conn = sqlite3.connect("analysis.db")
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute("""
            SELECT id, id_collector, timestamp, input_value, location, uv_index,
                   fitzpatrick_type, recommendations, status_message
            FROM analysis_log
            WHERE event_type = 'ANALYSIS'
        """)
        rows = sqlite_cursor.fetchall()
        print(f"DEBUG: export_db encontrou {len(rows)} linhas no SQLite")

        if not rows:
            sqlite_conn.close()
            return jsonify({"status": "error", "message": "Nenhuma análise para exportar."})

        # 2. Inserir mas apenas commit depois de todo loop
        mysql_conn = mysql.connector.connect(**DB_CONFIG)
        mysql_cursor = mysql_conn.cursor()
        #mysql_cursor.execute("""CREATE TABLE IF NOT EXISTS analises_pele ( ... )""")

        # Use apenas colunas, omitido aqui para brevidade
        mysql_conn.commit()
        mysql_cursor.close()
        mysql_conn.close()

        # Reabrir para inserir todos
        mysql_conn = mysql.connector.connect(**DB_CONFIG)
        mysql_cursor = mysql_conn.cursor()

        for row in rows:
            image_name = os.path.basename(row[3]) if row[3] else "N/A"
            mysql_cursor.execute("""
                INSERT INTO analises
                (id_colletor, data_hora, nome_imagem, localizacao,
                 indice_uv, tipo_pele, recomendacoes, estado)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                row[1] or ID_COLLECTOR,
                row[2],
                image_name,
                row[4] or "N/A",
                f"{row[5]:.1f}" if row[5] is not None else "0.0",
                row[6] or "N/A",
                row[7] or "N/A",
                row[8] or "Análise concluída"
            ))
        # 4. Commit e fechar conexão MySQL
        mysql_conn.commit()
        print("DEBUG: commit MySQL realizado")
        mysql_cursor.close()
        mysql_conn.close()

        # 5. Apagar registros do SQLite somente após commit no MySQL
        sqlite_cursor.execute("DELETE FROM analysis_log WHERE event_type = 'ANALYSIS'")
        deleted = sqlite_cursor.rowcount
        sqlite_conn.commit()
        print(f"DEBUG: apagou {deleted} linhas do SQLite")
        sqlite_cursor.close()
        sqlite_conn.close()

        return jsonify({
            "status": "success",
            "message": "Exportação concluída, commit MySQL realizado e registros locais apagados.",
            "quantidade_exportada": len(rows),
            "quantidade_apagada": deleted
        })

    except mysql.connector.Error as e:
        return jsonify({"status": "error", "message": f"Erro MySQL: {str(e)}"})
    except sqlite3.Error as e:
        return jsonify({"status": "error", "message": f"Erro SQLite: {str(e)}"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro geral: {str(e)}"})
'''

@app.route("/export_db", methods=["POST"])
def export_db():
    """Exporta dados do SQLite para MySQL incluindo imagens e apaga registros locais."""
    try:
        # 1. Buscar dados do SQLite
        with sqlite3.connect("analysis.db") as sqlite_conn:
            sqlite_cursor = sqlite_conn.cursor()
            sqlite_cursor.execute("""
                SELECT id, id_collector, timestamp, input_value, location, uv_index,
                       fitzpatrick_type, recommendations, status_message
                FROM analysis_log
                WHERE event_type = 'ANALYSIS'
            """)
            rows = sqlite_cursor.fetchall()

        if not rows:
            return jsonify({"status": "error", "message": "Nenhuma análise para exportar."})

        # 2. Conectar MySQL e inserir dados na tabela ANALISES
        mysql_conn = mysql.connector.connect(**DB_CONFIG)
        mysql_cursor = mysql_conn.cursor()
        
        saved_count = 0
        image_errors = []

        for row in rows:
            try:
                image_path = row[3]  # input_value contains the image path
                image_name = os.path.basename(image_path) if image_path else "N/A"
                image_blob = None

                # Read image file as binary data
                print(f"DEBUG: Processando imagem {image_name} do caminho {image_path}")
                if image_path and os.path.exists(image_path):
                    try:
                        with open(image_path, 'rb') as image_file:
                            image_blob = image_file.read()
                        print(f"DEBUG: Imagem {image_name} carregada ({len(image_blob)} bytes)")
                    except Exception as e:
                        image_errors.append(f"Erro ao ler {image_name}: {str(e)}")
                        print(f"DEBUG: Erro ao ler {image_name}: {str(e)}")

                # Insert into MySQL ANALISES table
                mysql_cursor.execute("""
                    INSERT INTO ANALISES
                    (id_colletor, data_hora, nome_imagem, imagem_blob, localizacao,
                     indice_uv, tipo_pele, recomendacoes, estado)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    row[1] or ID_COLLECTOR,
                    row[2],
                    image_name,
                    image_blob,
                    row[4] or "N/A",
                    f"{row[5]:.1f}" if row[5] is not None else "0.0",
                    row[6] or "N/A",
                    row[7] or "N/A",
                    row[8] or "Análise concluída"
                ))
                saved_count += 1

            except mysql.connector.Error as e:
                image_errors.append(f"MySQL error for row {row[0]}: {str(e)}")
                continue

        # 3. Commit MySQL
        mysql_conn.commit()
        print("DEBUG: MySQL commit realizado na tabela ANALISES")

        # 4. Delete images from filesystem after successful commit
        deleted_images = 0
        for row in rows:
            image_path = row[3]
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                    deleted_images += 1
                    print(f"DEBUG: Imagem {image_path} removida")
                except Exception as e:
                    image_errors.append(f"Erro ao remover {image_path}: {str(e)}")

        mysql_cursor.close()
        mysql_conn.close()

        # 5. Delete SQLite records
        with sqlite3.connect("analysis.db") as sqlite_conn:
            sqlite_cursor = sqlite_conn.cursor()
            sqlite_cursor.execute("DELETE FROM analysis_log WHERE event_type = 'ANALYSIS'")
            deleted_records = sqlite_cursor.rowcount
            sqlite_conn.commit()

        return jsonify({
            "status": "success",
            "message": "Exportação completa: dados e imagens salvos na tabela ANALISES!",
            "quantidade_exportada": saved_count,
            "quantidade_apagada": deleted_records,
            "imagens_movidas": deleted_images,
            "erros_imagem": image_errors if image_errors else None
        })

    except mysql.connector.Error as e:
        return jsonify({"status": "error", "message": f"Erro MySQL: {str(e)}"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Erro geral: {str(e)}"})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
