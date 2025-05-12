


<div align="center"><h1> DBCrafter </h1></div>

<div align="center">
  <a href="#">
    <img src="https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff" alt="Python Badge" width="100">
    <img src="https://img.shields.io/badge/Flask-000000?logo=flask&logoColor=fff" alt="Flask Badge" width="100">
    <img src="https://img.shields.io/badge/Pandas-150458?logo=pandas&logoColor=fff" alt="Pandas Badge" width="100">
    <img src="https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=fff" alt="Docker Badge" width="100">
  </a>
</div>

**DBCrafter is a lightweight web application that generates SQL `INSERT` statements from CSV files. Users can upload a file, specify the table name, and download an SQL script with the generated commands.**  

---

## 🌟 Features
- 📄 CSV, Excel & JSON Upload: Upload '.csv', '.xlsx' or '.json' files with the data to enter into the database.
- 📝 **Table Name Selection**: User defines the name of the destination table.
- ⚡ Automatic SQL Generation: Automatically creates 'INSERT INTO' commands based on the file.
- 💾 SQLite Integration: Inserts data directly into a local 'SQLite' database ('dados.db').
- 📥 Download SQL Script: Generates a '.sql' file with the insert commands to import into other databases.
---

## 🛠 Technologies Used
- **Python**: Core language for backend development.
- **Flask**: Micro web framework for handling routes and HTTP requests.
- **Pandas**: Used for reading and processing CSV files.
- **HTML & CSS**: Frontend user interface.
- **Docker**: For easy application deployment.
- SQLite3: Lightweight relational database used to store data locally.
  
---

## 🗃 Local Database (SQLite)
In addition to generating the 'INSERT' commands, the data is also automatically entered into the local 'dados.db' database.
This database can be accessed with any SQLite viewer (e.g., DB Browser for SQLite).

**Location:**
'src/dados.db'

## 🚀 Getting Started

### 🔹 Install Dependencies
If running locally (without Docker), install dependencies manually:
```bash
pip install flask pandas
```

### 🔹 Clone the Repository
```bash
git clone https://github.com/ThiagoRosa21/DBCrafter
cd DBCrafter
```

---

## 🏃 Running the Application

### **🔹 Running Locally (Without Docker)**
```bash
python src/main.py
```
🔗 **Access the application in your browser:**  
```bash
http://127.0.0.1:5000/
```

---

## 🐳 Running with Docker

### 🔹 **Build the Docker Image**
```bash
docker build -t insert-builder .
```

### 🔹 **Run the Docker Container**
```bash
docker run -d -p 5000:5000 --name DBCrafter-container DBCrafter
```

🔗 **Access the application in your browser:**  
```bash
http://localhost:5000/
```

### 🔹 **Stop and Remove the Container**
```bash
docker stop DBCrafter-container
docker rm DBCrafter-container
```

---

## 📂 Project Structure
```bash
DBCrafter/
├── src/
│   ├── __pycache__/               # Python cache files
│   ├── templates/                 # HTML templates
│   │   ├── homepage.html          # User interface template
│   ├── main.py                    # Flask main application file
│   ├── views.py                    # Route logic
├── Dockerfile                      # Docker configuration
├── docker-compose.yml               # Docker Compose file
├── README.md                        # Project documentation
```

---

## 📌 Example Usage
📂 **Input (CSV, Excel, JSON)**
<br>
csv
```
id,name,email
1,John Doe,john.doe@example.com
2,Jane Doe,jane.doe@example.com
```
json
```
[
  {"id": 1, "name": "Alice", "email": "alice@example.com"},
  {"id": 2, "name": "Bob", "email": "bob@example.com"}
]
```

📜 **Output (SQL)**
```sql
INSERT INTO clients (id, name, email) VALUES ('1', 'John Doe', 'john.doe@example.com');
INSERT INTO clients (id, name, email) VALUES ('2', 'Jane Doe', 'jane.doe@example.com');
```

---

# Access the link for this application:
```
https://dbcrafter.onrender.com/
```
## 🤝 Contributing
Pull requests are welcome! Please open an issue first to discuss any major changes.

---

## 📝 License
This project is licensed under the **MIT License**.  
📜 See the **LICENSE** file for more details.

---

