import os
import sys
from cs50 import SQL
from werkzeug.security import generate_password_hash

db_name = "dentist.db"

# 1. Precise Reset Logic
if os.path.exists(db_name):
    try:
        os.remove(db_name)
        print(f"✔ Old {db_name} removed.")
    except PermissionError:
        print(f"\n❌ ERROR: File '{db_name}' is locked. Close SQLite/Flask and try again.")
        sys.exit(1)

# 2. CREATE AN EMPTY FILE FIRST (Crucial for CS50 library)
open(db_name, 'w').close()
print(f"✔ New {db_name} file initialized.")

# 3. Connect to the (now existing) database
db = SQL(f"sqlite:///{db_name}")

def setup_normalized_db():
    print("Creating tables based on your schema...")
    
    # --- TABLE CREATION ---
    db.execute("CREATE TABLE roles (role_id INTEGER PRIMARY KEY AUTOINCREMENT, role_name TEXT NOT NULL UNIQUE)")
    db.execute("CREATE TABLE specialties (specialty_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE)")
    
    db.execute("""
        CREATE TABLE users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            dni TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            hash TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            birth_date DATE,
            phone TEXT,
            email TEXT,
            specialty_id INTEGER,
            start_time TIME,
            end_time TIME,
            role_id INTEGER NOT NULL,
            registration_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (specialty_id) REFERENCES specialties(specialty_id),
            FOREIGN KEY (role_id) REFERENCES roles(role_id)
        )
    """)

    db.execute("""
        CREATE TABLE patients (
            patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
            dni TEXT UNIQUE NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            birth_date DATE,
            phone TEXT,
            email TEXT,
            registration_date DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db.execute("""
        CREATE TABLE appointments (
            appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            appointment_date DATETIME NOT NULL,
            amount REAL,
            status TEXT DEFAULT 'scheduled',
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
            FOREIGN KEY (doctor_id) REFERENCES users(user_id)
        )
    """)

    db.execute("CREATE TABLE treatments (treatment_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, description TEXT, cost REAL)")

    db.execute("""
        CREATE TABLE medical_records (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            treatment_id INTEGER,
            diagnosis TEXT,
            date DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
            FOREIGN KEY (doctor_id) REFERENCES users(user_id),
            FOREIGN KEY (treatment_id) REFERENCES treatments(treatment_id)
        )
    """)

    # --- DATA INSERTION ---
    print("Inserting roles and specialties...")
    roles = ['sysadmin', 'owner', 'doctor', 'secretary']
    for r in roles:
        db.execute("INSERT INTO roles (role_name) VALUES (?)", r)
    
    db.execute("INSERT INTO specialties (name) VALUES (?)", 'General Dentistry')

    print("Generating user profiles...")
    initial_users = [
        ("0000000000", "sysadmin", "Horus", "System", "Admin", 1, None, None, None),
        ("1712345678", "owner_business", "Owner123", "Andres", "Boss", 2, None, None, None),
        ("1711111111", "doctor_house", "doctor123", "Gregory", "House", 3, 1, '08:00', '16:00'),
        ("1722222222", "secretaria_lucia", "secre123", "Lucia", "Mendez", 4, None, None, None)
    ]

    for dni, username, password, fname, lname, role_id, spec_id, start_time, end_time in initial_users:
        db.execute("""
            INSERT INTO users (dni, username, hash, first_name, last_name, role_id, specialty_id, start_time, end_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, dni, username, generate_password_hash(password), fname, lname, role_id, spec_id, start_time, end_time)

    print("\n--- SYSTEM READY ---")

if __name__ == "__main__":
    setup_normalized_db()