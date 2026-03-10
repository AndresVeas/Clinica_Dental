from cs50 import SQL
import random
from datetime import datetime, timedelta
import calendar

db = SQL("sqlite:///dentist.db")

def populate_mock_data():
    print("Starting data generation for charts...")

    # Nombres falsos
    first_names = ["Carlos", "Ana", "Luis", "Maria", "Jorge", "Lucia", "Jose", "Marta", "Pedro", "Sofia", "Diego", "Paula", "Andres", "Laura", "Miguel", "Carmen"]
    last_names = ["Gomez", "Lopez", "Diaz", "Martinez", "Perez", "Garcia", "Sanchez", "Romero", "Sosa", "Torres", "Ruiz", "Ramirez", "Flores", "Benitez", "Acosta", "Medina"]

    # 1. Crear 20 pacientes con números de cédula 
    print("Creating 20 new patients...")
    patient_ids = []
    base_cedula = 1750000000
    for _ in range(20):
        cedula = str(base_cedula + random.randint(10000, 999999))
        fn = random.choice(first_names)
        ln = random.choice(last_names)
        phone = f"09{random.randint(10000000, 99999999)}"
        email = f"{fn.lower()}.{ln.lower()}@example.com"
        
        try:
            id = db.execute("""
                INSERT INTO patients (cedula, first_name, last_name, phone, email) 
                VALUES (?, ?, ?, ?, ?)
            """, cedula, fn, ln, phone, email)
            patient_ids.append(id)
        except Exception:
            # En caso de cédula duplicada
            pass

    # Si por alguna razon no se crearon, recuperamos todos los existentes
    if not patient_ids:
        patients = db.execute("SELECT patient_id FROM patients")
        patient_ids = [p['patient_id'] for p in patients]

    # 2. Obtener Doctores existentes
    doctors = db.execute("SELECT user_id, specialty_id FROM users WHERE role_id = (SELECT role_id FROM roles WHERE role_name = 'doctor')")
    if not doctors:
        print("No doctors found! Please make sure there are doctors in the database first (run pupulate_data.py).")
        return

    doctor_ids = [d['user_id'] for d in doctors]

    # 3. Generar citas en los últimos 5 meses (incluyendo el actual)
    print("Generating appointments for the last 5 months...")
    current_date = datetime.now()
    
    # Rango de meses (0 = mes actual, 1 = mes anterior, ..., 4 = 4 meses atras)
    for i in range(5):
        month = current_date.month - i
        year = current_date.year
        if month <= 0:
            month += 12
            year -= 1
            
        _, num_days = calendar.monthrange(year, month)
        
        # Generamos entre 15 y 30 citas por mes
        num_appointments = random.randint(15, 30)
        
        for _ in range(num_appointments):
            # No generar en el futuro más allá de HOY si es el mes actual
            if i == 0 and current_date.day > 1:
                day = random.randint(1, current_date.day)
            else:
                day = random.randint(1, num_days)
                
            hour = random.randint(8, 17)
            minute = random.choice([0, 30])
            
            appt_date = datetime(year, month, day, hour, minute)
            
            status = 'completed' if appt_date < current_date else 'scheduled'
            
            p_id = random.choice(patient_ids)
            d_id = random.choice(doctor_ids)
            amount = round(random.uniform(30.0, 150.0), 2)
            
            try:
                db.execute("""
                    INSERT INTO appointments (patient_id, doctor_id, appointment_date, amount, status)
                    VALUES (?, ?, ?, ?, ?)
                """, p_id, d_id, appt_date.strftime("%Y-%m-%d %H:%M:%S"), amount, status)
            except Exception as e:
                print(f"Failed to insert appointment: {e}")

    print("--- SUCCESS ---")
    print("Mock data generated to visualize the charts perfectly.")

if __name__ == "__main__":
    populate_mock_data()
