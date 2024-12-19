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
    # Retrieve the uploaded file, table name, and file type from the request
    file = request.files.get('file-upload')
    table = request.form.get('table-name')
    limit = request.form.get('limit')
    archive_type = request.form.get('archive_type')  # Retrieve the file type from the select input
    
    # Check if a file was uploaded
    if not file:
        return "No file was uploaded."
    
    # Check if a table name was provided
    if not table:
        return "Table name is required."
    
    # Check if a file type was selected
    if not archive_type:
        return "File type is required."
    
    # Convert limit to integer (if provided)
    try:
        limit = int(limit) if limit else None
    except ValueError:
        return "Invalid limit value. Please provide a numeric value."

    try:
        # Read the file based on the selected type
        if archive_type == "excel":
            df = pd.read_excel(file) 
        elif archive_type == "csv":
            df = pd.read_csv(file)  
        else:
            return "Unsupported file type selected."
    except Exception as e:
        # Return an error message if the file cannot be processed
        return f"Error processing the file: {str(e)}"

    # Apply limit if provided
    if limit:
        df = df.head(limit)
    
    # List to store the generated SQL INSERT statements
    inserts = []

    # Loop through each row in the DataFrame
    for _, row in df.iterrows():
        values = []  
        
        # Process each value in the row
        for value in row:
            if isinstance(value, str):
                # Escape single quotes for SQL strings
                value = value.replace("'", "''")
                values.append(f"'{value}'")  
            elif pd.isnull(value):
                # Replace NaN values with NULL for SQL
                values.append("NULL")
            else:
                values.append(str(value))

        # Create the SQL INSERT statement for the current row
        insert = f"INSERT INTO {table} ({', '.join(df.columns)}) VALUES ({', '.join(values)});"
        inserts.append(insert)

    # Write all INSERT statements to a file
    output_file = os.path.join(os.path.dirname(__file__), 'inserts.sql')
    with open(output_file, 'w', encoding="utf-8") as f:
        f.write("\n".join(inserts))

    # Verify that the file was created
    if not os.path.exists(output_file):
        return "Error: The output file was not generated."

    # Send the generated SQL file as a downloadable response
    return send_file(
        output_file,
        as_attachment=True,
        download_name="inserts.sql",
        mimetype="text/plain"
    )
