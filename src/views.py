from main import app
from flask import render_template, request, send_file
import pandas as pd
import os

# Route for the homepage
@app.route("/")
def homepage_view():
    return render_template("homepage.html")

# Route to process the uploaded file and generate SQL INSERT statements
@app.route("/process", methods=["POST"])
def invite_archive():
    
    file = request.files.get('file-upload')
    table = request.form.get('table-name')
    limit = request.form.get('limit')
    archive_type = request.form.get('archive_type') 
    
  
    if not file:
        return "No file was uploaded."
    
  
    if not table:
        return "Table name is required."
    
   
    if not archive_type:
        return "File type is required."
    
   
    try:
        limit = int(limit) if limit else None
    except ValueError:
        return "Invalid limit value. Please provide a numeric value."

    try:
        
        if archive_type == "excel":
            df = pd.read_excel(file) 
        elif archive_type == "csv":
            df = pd.read_csv(file)  
        else:
            return "Unsupported file type selected."
    except Exception as e:
        
        return f"Error processing the file: {str(e)}"


    if limit:
        df = df.head(limit)
    

    inserts = []

 
    for _, row in df.iterrows():
        values = []  
        
      
        for value in row:
            if isinstance(value, str):
                
                value = value.replace("'", "''")
                values.append(f"'{value}'")  
            elif pd.isnull(value):
                
                values.append("NULL")
            else:
                values.append(str(value))

     
        insert = f"INSERT INTO {table} ({', '.join(df.columns)}) VALUES ({', '.join(values)});"
        inserts.append(insert)

    output_file = os.path.join(os.path.dirname(__file__), 'inserts.sql')
    with open(output_file, 'w', encoding="utf-8") as f:
        f.write("\n".join(inserts))


    if not os.path.exists(output_file):
        return "Error: The output file was not generated."

    return send_file(
        output_file,
        as_attachment=True,
        download_name="inserts.sql",
        mimetype="text/plain"
    )
