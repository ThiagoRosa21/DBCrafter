<div align="center"><h1> INSERT BUILDER 🚀 </h1></div>

<div align="center">
  <a href="#">
    <img src="https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff" alt="Python Badge" width="100">
    <img src="https://img.shields.io/badge/Flask-000000?logo=flask&logoColor=fff" alt="Flask Badge" width="100">
    <img src="https://img.shields.io/badge/Pandas-150458?logo=pandas&logoColor=fff" alt="Pandas Badge" width="100">
  </a>
</div>

**A lightweight web application to generate SQL `INSERT` commands from a CSV file. Users can upload a file, specify the table name, and download a script with the generated SQL commands. This project is ideal for automating data integration into relational databases.**

---

## Features
- 📄 **CSV Upload**: Upload a CSV file containing data to be inserted into a database.
- 📝 **Dynamic Table Selection**: Specify the name of the database table where data will be inserted.
- ⚡ **SQL Script Generation**: Automatically generates SQL `INSERT` statements based on the uploaded file and table name.
- 📥 **File Download**: Downloads the SQL script directly to your computer.

---

## Technologies Used 💻
- **Python**: The core language for backend development.
- **Flask**: A micro web framework for handling routes and HTTP requests.
- **Pandas**: Used for reading and processing CSV files.
- **HTML & CSS**: For building the web interface.

---

## Getting Started

### Install Dependencies
Run the following command to install Flask and Pandas in your environment:
```bash
pip install flask pandas
```
# Clone the Repository
```bash
git clone https://github.com/ThiagoRosa21/insert-builder
cd insert-builder
```
## Run the Application
### Start the Flask application:
```bash
python main.py
```
## Access the Application
### Open your browser and navigate to:
```bash
http://127.0.0.1:5000/
```
# Usage
- Upload a CSV file via the web interface.
- Enter the name of the database table.
- Click Enviar to generate the SQL script.
- Download the generated inserts.sql file.

# File Structure
```bash
Insert-Builder/
├── src
  ├── __Pycache__
  ├── Templates
    ├── homepage.html       # HTML template for the user interface
  ├── main.py             # Entry point for the Flask application
  ├── views.py            # Contains routes and business logic
```

# Example Workflow
Input: A CSV file with the following structure:
```bash
id,name,email
1,John Doe,john.doe@example.com
2,Jane Doe,jane.doe@example.com
```
### Output: A SQL script (inserts.sql) with:
```bash
INSERT INTO clients (id, name, email) VALUES ('1', 'John Doe', 'john.doe@example.com');
INSERT INTO clients (id, name, email) VALUES ('2', 'Jane Doe', 'jane.doe@example.com');
```
# Contributing
Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

