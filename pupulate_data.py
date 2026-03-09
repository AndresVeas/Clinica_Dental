from cs50 import SQL
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

# Conexión a la base de datos existente
db = SQL("sqlite:///dentist.db")

def populate():
    print("Iniciando carga de datos...")

    # 1. Insertar Especialidades adicionales
    specialties = ['Ortodoncia', 'Endodoncia', 'Cirugía Maxilofacial', 'Odontopediatría']
    for spec in specialties:
        try:
            # ACTUALIZADO: 'name' a 'description'
            db.execute("INSERT INTO specialties (description) VALUES (?)", spec)
        except:
            pass

    # 2. Insertar 4 Doctores (Role ID 3)
    # Contraseña para todos: doctor123
    doctors_data = [
        ("1755555551", "dr_smith", "John", "Smith", 2, "08:00", "16:00"), 
        ("1755555552", "dra_garcia", "Elena", "García", 3, "08:00", "16:00"), 
        ("1755555553", "dr_perez", "Carlos", "Pérez", 4, "09:00", "17:00"), 
        ("1755555554", "dra_lopez", "Ana", "López", 5, "09:00", "17:00")   
    ]

    print("Insertando doctores...")
    doctor_ids = []
    for cedula, user, fn, ln, spec_id, start_time, end_time in doctors_data:
        try:
            # ACTUALIZADO: 'dni' a 'cedula'
            id = db.execute("""
                INSERT INTO users (cedula, username, hash, first_name, last_name, role_id, specialty_id, start_time, end_time)
                VALUES (?, ?, ?, ?, ?, 3, ?, ?, ?)
            """, cedula, user, generate_password_hash("doctor123"), fn, ln, spec_id, start_time, end_time)
            doctor_ids.append(id)
        except:
            # Si ya existen, obtenemos sus IDs
            res = db.execute("SELECT user_id FROM users WHERE username = ?", user)
            doctor_ids.append(res[0]['user_id'])

    # 3. Insertar Pacientes de prueba
    print("Insertando pacientes...")
    patients_data = [
        ("1722222221", "Roberto", "Cano"),
        ("1722222222", "Maria", "Vaca"),
        ("1722222223", "Sebastian", "Rios"),
        ("1722222224", "Isabel", "Torres"),
        ("1722222225", "Mateo", "Paz")
    ]
    
    patient_ids = []
    for cedula, fn, ln in patients_data:
        try:
            # ACTUALIZADO: 'dni' a 'cedula'
            id = db.execute("INSERT INTO patients (cedula, first_name, last_name) VALUES (?, ?, ?)", cedula, fn, ln)
            patient_ids.append(id)
        except:
            res = db.execute("SELECT patient_id FROM patients WHERE cedula = ?", cedula)
            patient_ids.append(res[0]['patient_id'])

    # 4. Insertar 10 Citas (Respetando horario base 08:00 - 17:00)
    print("Programando 10 citas...")
    
    # Lista de citas: (Paciente_idx, Doctor_idx, Dias_desde_hoy, Hora, Monto)
    appointments_list = [
        (0, 0, 1, "09:00", 45.0), 
        (1, 0, 1, "10:30", 50.0),
        (2, 1, 2, "14:00", 120.0), 
        (3, 1, 2, "15:30", 35.0),
        (4, 2, 3, "08:00", 200.0),
        (0, 2, 3, "11:00", 60.0),
        (1, 3, 4, "09:45", 40.0),
        (2, 3, 4, "16:00", 55.0),
        (3, 0, 5, "13:00", 45.0),
        (4, 1, 5, "10:00", 85.0)
    ]

    base_date = datetime.now()
    
    for p_idx, d_idx, days, time_str, amount in appointments_list:
        app_date = (base_date + timedelta(days=days)).strftime('%Y-%m-%d')
        full_datetime = f"{app_date} {time_str}:00"
        
        db.execute("""
            INSERT INTO appointments (patient_id, doctor_id, appointment_date, amount, status)
            VALUES (?, ?, ?, ?, 'scheduled')
        """, patient_ids[p_idx], doctor_ids[d_idx], full_datetime, amount)

    print("\n--- CARGA EXITOSA ---")
    print("Se han creado 4 doctores, 5 pacientes y 10 citas distribuidas.")

if __name__ == "__main__":
    populate()