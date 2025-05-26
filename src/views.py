from flask import Flask, render_template, request, send_file, Response
import pandas as pd
import os
import sqlite3
import logging
from werkzeug.datastructures import FileStorage
import re

app = Flask(__name__)

# Configuração de log
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

DATABASE_NAME = "dados.db"
OUTPUT_FILE_NAME = "inserts.sql"


def create_database_connection(db_name: str) -> sqlite3.Connection:
    logger.debug(f"Conectando ao banco de dados: {db_name}")
    return sqlite3.connect(db_name)


def detect_sqlite_type(value) -> str:
    if isinstance(value, int):
        return "INTEGER"
    elif isinstance(value, float):
        return "REAL"
    else:
        return "TEXT"


def generate_table_schema(df: pd.DataFrame, table_name: str) -> str:
    columns_definitions = []
    for col in df.columns:
        sample_value = df[col].dropna().iloc[0] if not df[col].dropna().empty else ''
        col_type = detect_sqlite_type(sample_value)
        columns_definitions.append(f"{col} {col_type}")
    create_stmt = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns_definitions)});"
    logger.debug(f"Generated CREATE TABLE: {create_stmt}")
    return create_stmt


def sanitize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    def clean_column(col):
        col = str(col).strip()
        col = col.replace(" ", "_")
        col = col.replace("/", "_")
        col = col.replace("à", "a")
        col = re.sub(r"[^a-zA-Z0-9_]", "", col)
        return col

    df.columns = [clean_column(col) for col in df.columns]
    return df

def generate_insert_statements(df: pd.DataFrame, table_name: str) -> list:
    inserts = []
    for _, row in df.iterrows():
        values = []
        for value in row:
            if pd.isnull(value):
                values.append("NULL")
            elif isinstance(value, str):
                escaped = value.replace("'", "''")
                values.append(f"'{escaped}'")
            else:
                values.append(f"'{str(value)}'")
        insert_line = f"INSERT INTO {table_name} ({', '.join(df.columns)}) VALUES ({', '.join(values)});"
        inserts.append(insert_line)
    logger.debug(f"Geradas {len(inserts)} instruções INSERT")
    return inserts


def save_statements_to_file(statements: list, file_path: str):
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(statements))
    logger.debug(f"Instruções salvas em: {file_path}")


@app.route("/")
def homepage_view():
    return render_template("homepage.html")


@app.route("/process", methods=["POST"])
def invite_archive():
    file: FileStorage = request.files.get('file-upload')
    table: str = request.form.get('table-name')
    limit: str = request.form.get('limit')
    archive_type: str = request.form.get('archive_type')

    if not file:
        return Response("No file was uploaded.", status=400)
    if not table:
        return Response("Table name is required.", status=400)
    if not archive_type:
        return Response("File type is required.", status=400)

    try:
        limit = int(limit) if limit else None
    except ValueError:
        return Response("Invalid limit value. Please provide a numeric value.", status=400)

    try:
        if archive_type.lower() == "excel":
            df = pd.read_excel(file)
        elif archive_type.lower() == "csv":
            df = pd.read_csv(file)
        elif archive_type.lower() == "json":
            df = pd.read_json(file)
        else:
            return Response("Unsupported file type selected.", status=400)
    except Exception as e:
        logger.exception("Erro ao processar o arquivo.")
        return Response(f"Erro ao processar o arquivo: {str(e)}", status=500)

    if df.empty:
        return Response("Uploaded file has no data.", status=400)

    if limit:
        df = df.head(limit)

    df = sanitize_column_names(df)

    conn = create_database_connection(DATABASE_NAME)
    cursor = conn.cursor()

    try:
        create_table_sql = generate_table_schema(df, table)
        cursor.execute(create_table_sql)

        insert_sql = f"INSERT INTO {table} ({', '.join(df.columns)}) VALUES ({', '.join(['?'] * len(df.columns))})"
        for _, row in df.iterrows():
            clean_row = [None if pd.isnull(v) else str(v) for v in row]
            cursor.execute(insert_sql, clean_row)

        conn.commit()
    except sqlite3.DatabaseError as e:
        logger.exception("Erro no banco de dados.")
        conn.rollback()
        return Response(f"Erro no banco de dados: {str(e)}", status=500)
    finally:
        conn.close()

    inserts = generate_insert_statements(df, table)
    output_file_path = os.path.join(os.path.dirname(__file__), OUTPUT_FILE_NAME)
    save_statements_to_file(inserts, output_file_path)

    if not os.path.exists(output_file_path):
        return Response("Error: The output file was not generated.", status=500)

    return send_file(
        output_file_path,
        as_attachment=True,
        download_name=OUTPUT_FILE_NAME,
        mimetype="text/plain"
    )
