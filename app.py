from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from helper import login_required, role_required
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, date, timedelta

app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///dentist.db")

@app.route("/")
@login_required
def index():
    role = session.get("user_role")
    if role == "doctor":
        return redirect("/doctor")
    if role == "secretary":
        return redirect("/secretary")
    if role == "owner":
        return redirect("/owner/dashboard")
    if role == "sysadmin":
        return redirect("/owner/dashboard")

    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username:
            flash("Must provide username", "danger")
            return redirect("/login")
        elif not password:
            flash("Must provide password", "danger")
            return redirect("/login")

        rows = db.execute("""
            SELECT users.*, roles.role_name 
            FROM users 
            JOIN roles ON users.role_id = roles.role_id 
            WHERE users.username = ?
        """, username)

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            flash("Invalid username and/or password", "danger")
            return redirect("/login")

        session["user_id"] = rows[0]["user_id"]
        session["user_role"] = rows[0]["role_name"]
        session["username"] = rows[0].get("first_name") or rows[0].get("username") or username

        flash(f"Welcome back, {session['username']}!", "success")
        return redirect("/")
    else:
        return render_template("login.html")
    
    
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/profile/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    user_id = session.get("user_id")
    if request.method == "POST":
        current_password = request.form.get("old_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if not current_password or not new_password or not confirm_password:
            flash("All fields are required.", "danger")
            return redirect("/profile/change-password")

        if new_password != confirm_password:
            flash("New passwords do not match.", "danger")
            return redirect("/profile/change-password")

        if len(new_password) < 6:
            flash("New password must be at least 6 characters.", "danger")
            return redirect("/profile/change-password")

        try:
            rows = db.execute("SELECT hash FROM users WHERE user_id = ?", user_id)
        except Exception:
            rows = []

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], current_password):
            flash("Current password is incorrect.", "danger")
            return redirect("/profile/change-password")

        try:
            new_hash = generate_password_hash(new_password)
            db.execute("UPDATE users SET hash = ? WHERE user_id = ?", new_hash, user_id)
            flash("Password updated successfully.", "success")
        except Exception:
            flash("Unable to update password. Try again later.", "danger")

        return redirect("/")

    return render_template("change_password.html")


# =========================================================
# DOCTOR ROUTES
# =========================================================

@app.route("/doctor", methods=["GET", "POST"])
@login_required
@role_required("doctor")
def doctor_dashboard():
    doctor_id = session.get("user_id")
    today = date.today().isoformat()
    
    if request.method == "POST":
        attended_ids = request.form.getlist("attended")
        try:
            for aid in attended_ids:
                db.execute("UPDATE appointments SET status = 'attended' WHERE appointment_id = ?", int(aid))
            flash("Attendance successfully updated.", "success")
        except Exception:
            flash("Error updating attendance.", "danger")
        return redirect("/doctor")

    try:
        # Se agrega p.cedula a la consulta
        appointments = db.execute(
            """
            SELECT a.appointment_id, p.cedula, p.first_name || ' ' || p.last_name AS patient_name, 
                   date(a.appointment_date) AS appointment_date,
                   time(a.appointment_date) AS appointment_time, a.status
            FROM appointments a
            JOIN patients p ON a.patient_id = p.patient_id
            WHERE a.doctor_id = ? AND date(a.appointment_date) = ? AND a.status = 'scheduled'
            ORDER BY a.appointment_date ASC
            LIMIT 10
            """,
            doctor_id, today
        )
    except Exception:
        appointments = []

    return render_template("doctor_dashboard.html", appointments=appointments, data={
        "specialties": [],
        "earnings": [],
        "appointments_count": []
    })


@app.route("/doctor/appointments")
@login_required
@role_required("doctor")
def doctor_appointments():
    doctor_id = session.get("user_id")
    try:
        # Se agrega p.cedula a la consulta
        appointments = db.execute(
            """
            SELECT a.appointment_id, p.cedula, p.first_name || ' ' || p.last_name AS patient_name, 
                   date(a.appointment_date) AS appointment_date,
                   time(a.appointment_date) AS appointment_time, a.status
            FROM appointments a
            JOIN patients p ON a.patient_id = p.patient_id
            WHERE a.doctor_id = ?
            ORDER BY a.appointment_date ASC
            LIMIT 50
            """,
            doctor_id
        )
    except Exception:
        appointments = []
    return render_template("doctor_appointments.html", appointments=appointments)


# =========================================================
# SECRETARY ROUTES
# =========================================================

@app.route("/secretary")
@login_required
@role_required("secretary")
def secretary_dashboard():
    try:
        # Se agrega p.cedula a la consulta
        appointments = db.execute(
            """
            SELECT a.appointment_id, p.cedula,
                   date(a.appointment_date) AS appointment_date,
                   time(a.appointment_date) AS appointment_time, a.status,
                   p.first_name || ' ' || p.last_name AS patient_name,
                   u.first_name || ' ' || u.last_name AS doctor_name
            FROM appointments a
            JOIN patients p ON a.patient_id = p.patient_id
            JOIN users u ON a.doctor_id = u.user_id
            WHERE a.appointment_date >= datetime('now', 'localtime', '-10 minutes')
              AND a.appointment_date <= datetime('now', 'localtime', '+10 minutes')
            ORDER BY a.appointment_date ASC
            LIMIT 10
            """
        )
    except Exception:
        appointments = []
    return render_template("secretary_dashboard.html", appointments=appointments)


@app.route("/secretary/doctors")
@login_required
@role_required("secretary")
def secretary_doctors():
    try:
        doctors = db.execute(
            """
            SELECT u.user_id, u.first_name, u.last_name, u.username,
                   u.start_time, u.end_time, s.description AS specialty,
                   (SELECT COUNT(*) FROM appointments a WHERE a.doctor_id = u.user_id AND a.status = 'scheduled') AS active_appointments
            FROM users u
            JOIN roles r ON u.role_id = r.role_id
            LEFT JOIN specialties s ON u.specialty_id = s.specialty_id
            WHERE r.role_name = 'doctor'
            """
        )
    except Exception:
        doctors = []
    return render_template("secretary_doctors.html", doctors=doctors)


@app.route("/secretary/appointments")
@login_required
@role_required("secretary")
def secretary_appointments():
    try:
        # Se agrega p.cedula a la consulta
        appointments = db.execute(
            """
            SELECT a.appointment_id, p.cedula,
                   date(a.appointment_date) AS appointment_date,
                   time(a.appointment_date) AS appointment_time, a.status,
                   p.first_name || ' ' || p.last_name AS patient_name,
                   u.first_name || ' ' || u.last_name AS doctor_name
            FROM appointments a
            JOIN patients p ON a.patient_id = p.patient_id
            JOIN users u ON a.doctor_id = u.user_id
            ORDER BY a.appointment_date DESC
            """
        )
    except Exception:
        appointments = []
    return render_template("secretary_appointments.html", appointments=appointments)


@app.route("/secretary/register_appointment", methods=["GET", "POST"])
@login_required
@role_required("secretary")
def secretary_register_appointment():
    if request.method == "POST":
        patient_id = request.form.get("patient_id")
        doctor_id = request.form.get("doctor_id")
        appointment_date = request.form.get("appointment_date")
        appointment_time = request.form.get("appointment_time")
        status = request.form.get("status")
        
        full_datetime = f"{appointment_date} {appointment_time}:00"

        existing = db.execute("""
            SELECT appointment_id FROM appointments 
            WHERE doctor_id = ? AND appointment_date = ? AND status != 'cancelled'
        """, doctor_id, full_datetime)

        if existing:
            flash("This time slot is already booked.", "danger")
            return redirect("/secretary/register_appointment")
        
        try:
            db.execute("""
                INSERT INTO appointments (patient_id, doctor_id, appointment_date, status) 
                VALUES (?, ?, ?, ?)
            """, patient_id, doctor_id, full_datetime, status)
            flash("Appointment scheduled successfully!", "success")
            return redirect("/secretary")
        except Exception:
            flash("Error scheduling appointment.", "danger")

    doctors = db.execute("SELECT user_id, first_name, last_name FROM users WHERE role_id = (SELECT role_id FROM roles WHERE role_name = 'doctor')")
    specialties = db.execute("SELECT specialty_id, description FROM specialties")
    
    return render_template("secretary_register_appointment.html", doctors=doctors, specialties=specialties)


@app.route("/secretary/register_patient", methods=["GET", "POST"])
@login_required
@role_required("secretary")
def secretary_register_patient():
    if request.method == "POST":
        # Nombres de variables sincronizados con el HTML en inglés
        cedula = request.form.get("id_number")
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        phone = request.form.get("phone")
        email = request.form.get("email")
        birth_date = request.form.get("birth_date")

        # Validación para evitar AttributeError
        if not first_name or not last_name:
            flash("First and Last names are required.", "danger")
            return redirect("/secretary/register_patient")

        try:
            db.execute("""
                INSERT INTO patients (cedula, first_name, last_name, phone, email, birth_date) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, cedula, first_name.upper(), last_name.upper(), phone, email, birth_date)
            flash("Patient registered successfully!", "success")
            return redirect("/secretary")
        except Exception:
            flash("Error: Patient ID might already exist.", "danger")
            
    return render_template("secretary_register_patient.html")


# =========================================================
# API ROUTES
# =========================================================

@app.route("/api/get_patient/<cedula>")
@login_required
@role_required("secretary")
def get_patient(cedula):
    try:
        # Se usa 'cedula' para coincidir con la base de datos
        rows = db.execute("SELECT patient_id, first_name, last_name FROM patients WHERE cedula = ?", cedula)
        if len(rows) == 1:
            return jsonify({"success": True, "patient": rows[0]})
        return jsonify({"success": False})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/available_slots")
@login_required
@role_required("secretary")
def available_slots():
    doctor_id = request.args.get("doctor_id")
    date_str = request.args.get("date")

    if not doctor_id or not date_str:
        return jsonify({"slots": []})

    doctor = db.execute("SELECT start_time, end_time FROM users WHERE user_id = ?", doctor_id)
    if not doctor or not doctor[0]["start_time"] or not doctor[0]["end_time"]:
        return jsonify({"slots": []})

    start_time_str = doctor[0]["start_time"][:5] 
    end_time_str = doctor[0]["end_time"][:5]

    try:
        start_dt = datetime.strptime(f"{date_str} {start_time_str}", "%Y-%m-%d %H:%M")
        end_dt = datetime.strptime(f"{date_str} {end_time_str}", "%Y-%m-%d %H:%M")
    except ValueError:
        return jsonify({"slots": []})

    appointments = db.execute("""
        SELECT time(appointment_date) as appt_time 
        FROM appointments 
        WHERE doctor_id = ? AND date(appointment_date) = ? AND status != 'cancelled'
    """, doctor_id, date_str)

    booked_times = [appt["appt_time"][:5] for appt in appointments]

    slots = []
    current_dt = start_dt
    while current_dt + timedelta(minutes=30) <= end_dt:
        slot_str = current_dt.strftime("%H:%M")
        if slot_str not in booked_times:
            slots.append(slot_str)
        current_dt += timedelta(minutes=30)

    return jsonify({"slots": slots})


# -------------------------
# OWNER ROUTES
# -------------------------
@app.route("/owner/dashboard")
@login_required
@role_required("owner")
def owner_dashboard():
    chart_data = {
        "specialties": ["Orthodontics", "Endodontics", "Surgery", "Pediatrics"],
        "earnings": [1500, 800, 2200, 1100],
        "appointments_count": [45, 20, 15, 30]
    }
    return render_template("owner_dashboard.html", data=chart_data)


@app.route("/owner/doctors")
@login_required
@role_required("owner")
def owner_doctors():
    try:
        doctors = db.execute(
            """
            SELECT u.user_id, u.first_name, u.last_name, u.username,
                   u.start_time, u.end_time, s.description AS specialty,
                   (SELECT COUNT(*) FROM appointments a WHERE a.doctor_id = u.user_id AND a.status = 'scheduled') AS active_appointments
            FROM users u
            JOIN roles r ON u.role_id = r.role_id
            LEFT JOIN specialties s ON u.specialty_id = s.specialty_id
            WHERE r.role_name = 'doctor'
            """
        )
    except Exception:
        doctors = []
    return render_template("owner_doctors.html", doctors=doctors)