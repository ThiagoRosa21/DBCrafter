from main import app
from flask import render_template, request, send_file
import pandas as pd

@app.route("/")
def homepage():
    return render_template("homepage.html")

@app.route("/process", methods=["POST"])
def invite_archive():
    file = request.files.get('file-upload')
    table = request.form.get('table-name')
    if not file:
        return "Nenhum arquivo foi enviado."

    try:
        # Carrega o arquivo CSV em um DataFrame
        df = pd.read_csv(file)
    except Exception as e:
        return f"Erro ao processar o arquivo: {str(e)}"

    # Lista para armazenar os comandos INSERT
    inserts = []

    for _, row in df.iterrows():
        values = []
        for value in row:
            if isinstance(value, str):
                value = value.replace("'", "''")  # Escapa aspas simples para SQL
                values.append(f"'{value}'")
            elif pd.isnull(value):  # Tratamento de valores nulos
                values.append("NULL")
            else:
                values.append(str(value))

        # Criação do comando INSERT
        insert = f"INSERT INTO {table} ({', '.join(df.columns)}) VALUES ({', '.join(values)});"
        inserts.append(insert)

    # Salvando os comandos no arquivo
    output_file = "inserts.sql"
    with open(output_file, 'w', encoding="utf-8") as f:
        f.write("\n".join(inserts))

    # Envia o arquivo para download pelo navegador
    return send_file(
        output_file,
        as_attachment=True,
        download_name="inserts.sql",
        mimetype="text/plain"
    )
