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
    """Redirect logged-in users to their role-specific landing page.

    Falls back to a generic index if role is unknown.
    """
    role = session.get("user_role")
    if role == "doctor":
        return redirect("/doctor")
    if role == "secretary":
        return redirect("/secretary")
    if role == "owner":
        return redirect("/owner/dashboard")
    # sysadmin has full access — send to owner dashboard for now
    if role == "sysadmin":
        return redirect("/owner/dashboard")

    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        username = request.form.get("username")
        password = request.form.get("password")

        if not username:
            flash("Must provide username", "danger")
            return redirect("/login")

        # Ensure password was submitted
        elif not password:
            flash("Must provide password", "danger")
            return redirect("/login")

        # Query database for username joining with roles table
        # We need the role_name for the @role_required decorator
        rows = db.execute("""
            SELECT users.*, roles.role_name 
            FROM users 
            JOIN roles ON users.role_id = roles.role_id 
            WHERE users.username = ?
        """, username)

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
            flash("Invalid username and/or password", "danger")
            return redirect("/login")

        # Remember which user has logged in
        session["user_id"] = rows[0]["user_id"]
        session["user_role"] = rows[0]["role_name"]  # Stores 'owner', 'doctor', 'secretary', or 'sysadmin'
        # store a display name for the profile dropdown
        session["username"] = rows[0].get("first_name") or rows[0].get("username") or username

        # Redirect user to home page
        flash(f"Welcome back, {rows[0].get('first_name') or rows[0].get('username') }!", "success")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")
    
    
@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
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

        # Verify current password
        try:
            rows = db.execute("SELECT hash FROM users WHERE user_id = ?", user_id)
        except Exception:
            rows = []

        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], current_password):
            flash("Current password is incorrect.", "danger")
            return redirect("/profile/change-password")

        # Update password
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
    """Doctor main page: first 10 scheduled appointments for today."""
    doctor_id = session.get("user_id")
    today = date.today().isoformat()
    
    if request.method == "POST":
        attended_ids = request.form.getlist("attended")
        try:
            for aid in attended_ids:
                db.execute("UPDATE appointments SET status = 'attended' WHERE appointment_id = ?", int(aid))
            flash("Attendance successfully updated.", "success")
        except Exception as e:
            flash("Error updating attendance.", "danger")
            print(e)
        return redirect("/doctor")

    try:
        appointments = db.execute(
            """
            SELECT a.appointment_id, p.first_name || ' ' || p.last_name AS patient_name, 
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
    except Exception as e:
        print(e)
        appointments = []

    return render_template("doctor_dashboard.html", appointments=appointments)


@app.route("/doctor/appointments")
@login_required
@role_required("doctor")
def doctor_appointments():
    """List first 50 appointments for the doctor."""
    doctor_id = session.get("user_id")
    try:
        appointments = db.execute(
            """
            SELECT a.appointment_id, p.first_name || ' ' || p.last_name AS patient_name, 
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
    except Exception as e:
        print(e)
        appointments = []
    return render_template("doctor_appointments.html", appointments=appointments)


# =========================================================
# SECRETARY ROUTES
# =========================================================

@app.route("/secretary")
@login_required
@role_required("secretary")
def secretary_dashboard():
    """Secretary main page: appointments +/- 10 minutes from now."""
    try:
        appointments = db.execute(
            """
            SELECT a.appointment_id, 
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
    except Exception as e:
        print(e)
        appointments = []
    return render_template("secretary_dashboard.html", appointments=appointments)


@app.route("/secretary/doctors")
@login_required
@role_required("secretary")
def secretary_doctors():
    """List employed doctors with a virtual active-appointments column."""
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
    except Exception as e:
        print(e)
        doctors = []
    return render_template("secretary_doctors.html", doctors=doctors)


@app.route("/secretary/appointments")
@login_required
@role_required("secretary")
def secretary_appointments():
    """Full appointments list for secretary."""
    try:
        appointments = db.execute(
            """
            SELECT a.appointment_id, 
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
    except Exception as e:
        print(e)
        appointments = []
    return render_template("secretary_appointments.html", appointments=appointments)


@app.route("/secretary/register_appointment", methods=["GET", "POST"])
@login_required
@role_required("secretary")
def secretary_register_appointment():
    if request.method == "POST":
        patient_id = request.form.get("patient_id")
        doctor_id = request.form.get("doctor_id")
        fecha = request.form.get("fecha_cita")
        hora = request.form.get("hora_cita")
        estado = request.form.get("estado")
        
        appointment_date = f"{fecha} {hora}:00"

        # Validar doble reserva
        existing = db.execute("""
            SELECT appointment_id FROM appointments 
            WHERE doctor_id = ? AND appointment_date = ? AND status != 'cancelled'
        """, doctor_id, appointment_date)

        if existing:
            flash("This time slot is already booked. Please select another.", "danger")
            return redirect("/secretary/register_appointment")
        
        try:
            db.execute("""
                INSERT INTO appointments (patient_id, doctor_id, appointment_date, status) 
                VALUES (?, ?, ?, ?)
            """, patient_id, doctor_id, appointment_date, estado)
            flash("Appointment scheduled successfully!", "success")
            return redirect("/secretary")
        except Exception as e:
            print(e)
            flash("Error scheduling appointment.", "danger")

    # GET: Cargar doctores y especialidades
    doctors = db.execute("SELECT user_id, first_name, last_name FROM users WHERE role_id = (SELECT role_id FROM roles WHERE role_name = 'doctor')")
    specialties = db.execute("SELECT specialty_id, name AS description FROM specialties")
    
    return render_template("secretary_register_appointment.html", doctors=doctors, specialties=specialties)


@app.route("/secretary/register_patient", methods=["GET", "POST"])
@login_required
@role_required("secretary")
def secretary_register_patient():
    if request.method == "POST":
        cedula = request.form.get("cedula")
        first_name = request.form.get("nombres").upper()
        last_name = request.form.get("apellidos").upper()
        phone = request.form.get("celular")
        email = request.form.get("correo")
        birth_date = request.form.get("fecha_nacimiento")

        try:
            # Usar 'dni' internamente para que coincida con tu base de datos actual
            db.execute("""
                INSERT INTO patients (dni, first_name, last_name, phone, email, birth_date) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, cedula, first_name, last_name, phone, email, birth_date)
            flash("Patient registered successfully!", "success")
            return redirect("/secretary")
        except Exception as e:
            print(e)
            flash("Error registering patient. ID might already exist.", "danger")
            
    return render_template("secretary_register_patient.html")


# =========================================================
# API ROUTES (Para uso interno de JS)
# =========================================================

@app.route("/api/get_patient/<cedula>")
@login_required
@role_required("secretary")
def get_patient(cedula):
    """Busca al paciente usando 'dni' para evitar el error de columna"""
    try:
        rows = db.execute("SELECT patient_id, first_name, last_name FROM patients WHERE dni = ?", cedula)
        if len(rows) == 1:
            return jsonify({"success": True, "patient": rows[0]})
        return jsonify({"success": False})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/available_slots")
@login_required
@role_required("secretary")
def available_slots():
    """Calcula los bloques de 30 minutos libres para un doctor en una fecha."""
    doctor_id = request.args.get("doctor_id")
    date_str = request.args.get("date")

    if not doctor_id or not date_str:
        return jsonify({"slots": []})

    # 1. Obtener horario de trabajo del doctor
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

    # 2. Buscar qué citas ya existen
    appointments = db.execute("""
        SELECT time(appointment_date) as appt_time 
        FROM appointments 
        WHERE doctor_id = ? AND date(appointment_date) = ? AND status != 'cancelled'
    """, doctor_id, date_str)

    booked_times = [appt["appt_time"][:5] for appt in appointments]

    # 3. Generar los intervalos de 30 minutos
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
    """Owner analytics dashboard with Chart.js placeholders."""
    # Dummy data for chart representation (you will link this to db.execute later)
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
    except Exception as e:
        print(e)
        doctors = []
    return render_template("owner_doctors.html", doctors=doctors)