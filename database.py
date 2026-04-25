from sqlite3 import Cursor

import mysql.connector
from mysql.connector import Error

# Database connection configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'NewPassword123!',  # Replace with your MySQL password
}

def create_connection():
    """Create a database connection to MySQL"""
    try:
        connection = mysql.connector.connect(
            host=db_config['host'],
            user=db_config['user'],
            password=db_config['password']
        )
        if connection.is_connected():
            print("Successfully connected to MySQL database")
            return connection
    except Error as e:
        print(f"Error: {e}")
        return None

def create_database(connection):
    """Create the imhotep_db database"""
    cursor = connection.cursor()
    try:
        cursor.execute("CREATE DATABASE IF NOT EXISTS imhotep_db")
        print("Database created successfully")
        cursor.close()
    except Error as e:
        print(f"Error: {e}")

def create_tables(connection):
    """Create tables for the HR and recruitment module"""
    cursor = connection.cursor()
    
    # Jobs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS imhotep_db.jobs (
        job_id INT AUTO_INCREMENT PRIMARY KEY,
        job_title VARCHAR(255) NOT NULL,
        job_description TEXT,
        department VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Candidates table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS imhotep_db.candidates (
        candidate_id INT AUTO_INCREMENT PRIMARY KEY,
        first_name VARCHAR(100) NOT NULL,
        last_name VARCHAR(100) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        phone VARCHAR(20),
        resume_path VARCHAR(255),
        applied_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Job applications table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS imhotep_db.job_applications (
        application_id INT AUTO_INCREMENT PRIMARY KEY,
        candidate_id INT NOT NULL,
        job_id INT NOT NULL,
        status VARCHAR(50) DEFAULT 'Applied',
        application_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (candidate_id) REFERENCES imhotep_db.candidates(candidate_id),
        FOREIGN KEY (job_id) REFERENCES imhotep_db.jobs(job_id)
    )
    """)
    
    connection.commit()
    print("Tables created successfully!")
    cursor.close()

if __name__ == "__main__":
    conn = create_connection()
    if conn:
        create_database(conn)
        create_tables(conn)
        Cursor = conn.cursor()
        Cursor.execute("INSERT INTO imhotep_db.jobs (job_title, job_description, department) VALUES ('Software Engineer', 'Build software', 'Engineering')")
        Cursor.execute("INSERT INTO imhotep_db.jobs (job_title, job_description, department) VALUES ('HR Manager', 'Manage hiring', 'HR')")
        conn.commit()        
        Cursor.execute("SELECT * FROM imhotep_db.jobs")
        jobs = Cursor.fetchall()
        print("\n  --JOBS ADDED--")
        for job in jobs:
            print(f"Job ID: {job[0]} | Title: {job[1]} | Department: {job[3]}")
        Cursor.close()
        conn.close()