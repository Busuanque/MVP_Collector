import sqlite3
import os
from datetime import datetime

def query_db():
    """Query the analysis_log table and display each analysis with its unique image name."""
    db_path = "E:\\OneDrive\\02. IPCB\\Prototipo\\MVP_V2\\analysis.db"
    try:
        # Connect to the database
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            # Verify table exists and get schema
            cursor.execute("PRAGMA table_info(analysis_log)")
            columns = [col[1] for col in cursor.fetchall()]
            expected_columns = [
                "id", "timestamp", "event_type", "input_type", "input_value",
                "location", "uv_index", "fitzpatrick_type", "recommendations", "status_message"
            ]
            if not all(col in columns for col in expected_columns):
                print("Erro: O esquema da tabela analysis_log está incompleto. Colunas esperadas:", expected_columns)
                print("Colunas encontradas:", columns)
                return

            # Query all rows
            cursor.execute("SELECT * FROM analysis_log WHERE event_type = 'ANALYSIS'")
            rows = cursor.fetchall()

            if not rows:
                print("Nenhum registo de análise encontrado na tabela analysis_log.")
                return

            # Print header
            print("Registos de Análises:")
            print("-" * 80)

            # Print each row as a single line
            for row in rows:
                # Map row to column names
                row_dict = {
                    "ID": row[0],
                    "Data/Hora": row[1],
                    "Nome da Imagem": os.path.basename(row[4]) if row[4] else "N/A",
                    "Localização": row[5] if row[5] else "N/A",
                    "Índice UV": f"{row[6]:.1f}" if row[6] is not None else "N/A",
                    "Tipo de Pele": row[7] if row[7] else "N/A",
                    "Recomendações": row[8] if row[8] else "N/A",
                    "Mensagem": row[9] if row[9] else "N/A"
                }
                # Format row as a single line
                line = (
                    f"ID: {row_dict['ID']}, "
                    f"Data/Hora: {row_dict['Data/Hora']}, "
                    f"Nome da Imagem: {row_dict['Nome da Imagem']}, "
                    f"Localização: {row_dict['Localização']}, "
                    f"Índice UV: {row_dict['Índice UV']}, "
                    f"Tipo de Pele: {row_dict['Tipo de Pele']}, "
                    f"Recomendações: {row_dict['Recomendações']}, "
                    f"Mensagem: {row_dict['Mensagem']}"
                )
                print(line)

    except sqlite3.Error as e:
        print(f"Erro na base de dados: {str(e)}")
    except FileNotFoundError:
        print(f"Erro: O ficheiro {db_path} não foi encontrado.")
    except Exception as e:
        print(f"Erro inesperado: {str(e)}")

if __name__ == "__main__":
    print(f"Consulta iniciada em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    query_db()