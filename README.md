Here is your **updated `README.md`** in **English** with all improvements in a **single code block**. 🚀  


<div align="center"><h1> INSERT BUILDER 🚀 </h1></div>

<div align="center">
  <a href="#">
    <img src="https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff" alt="Python Badge" width="100">
    <img src="https://img.shields.io/badge/Flask-000000?logo=flask&logoColor=fff" alt="Flask Badge" width="100">
    <img src="https://img.shields.io/badge/Pandas-150458?logo=pandas&logoColor=fff" alt="Pandas Badge" width="100">
    <img src="https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=fff" alt="Docker Badge" width="100">
  </a>
</div>

**Insert Builder is a lightweight web application that generates SQL `INSERT` statements from CSV files. Users can upload a file, specify the table name, and download an SQL script with the generated commands.**  

---

## 🌟 Features
- 📄 **CSV Upload**: Upload a CSV file containing data for database insertion.
- 📝 **Table Name Selection**: Users can define the target database table.
- ⚡ **Automatic SQL Generation**: Creates `INSERT INTO` statements based on the uploaded file.
- 📥 **Download SQL Script**: Users can download the `.sql` file for database import.

---

## 🛠 Technologies Used
- **Python**: Core language for backend development.
- **Flask**: Micro web framework for handling routes and HTTP requests.
- **Pandas**: Used for reading and processing CSV files.
- **HTML & CSS**: Frontend user interface.
- **Docker**: For easy application deployment.

---

## 🚀 Getting Started

### 🔹 Install Dependencies
If running locally (without Docker), install dependencies manually:
```bash
pip install flask pandas
```

### 🔹 Clone the Repository
```bash
git clone https://github.com/ThiagoRosa21/Insert-Builder
cd Insert-Builder
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
docker run -d -p 5000:5000 --name insert-builder-container insert-builder
```

🔗 **Access the application in your browser:**  
```bash
http://localhost:5000/
```

### 🔹 **Stop and Remove the Container**
```bash
docker stop insert-builder-container
docker rm insert-builder-container
```

---

## 📂 Project Structure
```bash
Insert-Builder/
├── src/
│   ├── __pycache__/               # Python cache files
│   ├── templates/                 # HTML templates
│   │   ├── homepage.html          # User interface template
│   ├── main.py                    # Flask main application file
│   ├── views.py                    # Route logic
│   ├── requirements.txt            # Project dependencies
├── Dockerfile                      # Docker configuration
├── docker-compose.yml               # Docker Compose file
├── README.md                        # Project documentation
```

---

## 📌 Example Usage
📂 **Input (CSV)**
```csv
id,name,email
1,John Doe,john.doe@example.com
2,Jane Doe,jane.doe@example.com
```

📜 **Output (SQL)**
```sql
INSERT INTO clients (id, name, email) VALUES ('1', 'John Doe', 'john.doe@example.com');
INSERT INTO clients (id, name, email) VALUES ('2', 'Jane Doe', 'jane.doe@example.com');
```

---

## 🤝 Contributing
Pull requests are welcome! Please open an issue first to discuss any major changes.

---

## 📝 License
This project is licensed under the **MIT License**.  
📜 See the **LICENSE** file for more details.

---

