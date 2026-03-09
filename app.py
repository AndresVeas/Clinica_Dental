from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
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


# -------------------------
# Role-specific routes
# -------------------------


@app.route("/doctor", methods=["GET", "POST"])
@login_required
@role_required("doctor")
def doctor_dashboard():
    """Doctor main page: first 10 appointments for today (checkboxes to mark attended)."""
    doctor_id = session.get("user_id")
    today = date.today().isoformat()
    try:
        appointments = db.execute(
            """
            SELECT a.appointment_id, p.first_name || ' ' || p.last_name AS patient_name, a.appointment_date AS appointment_time, a.status
            FROM appointments a
            JOIN patients p ON a.patient_id = p.patient_id
            WHERE a.doctor_id = ? AND date(a.appointment_date) = ?
            ORDER BY a.appointment_date ASC
            LIMIT 10
            """,
            doctor_id, today
        )
    except Exception as e:
        print(e)
        appointments = []

    if request.method == "POST":
        attended_ids = request.form.getlist("attended")
        try:
            # mark checked appointments as attended
            for aid in attended_ids:
                db.execute("UPDATE appointments SET status = ? WHERE appointment_id = ?", "attended", int(aid))

            # mark other visible appointments as scheduled (unchecked)
            ids_today = [str(a.get("appointment_id")) for a in appointments if a.get("appointment_id") is not None]
            for aid in ids_today:
                if aid not in attended_ids:
                    db.execute("UPDATE appointments SET status = ? WHERE appointment_id = ?", "scheduled", int(aid))
        except Exception:
            pass
        flash("Attendance updated.", "success")
        return redirect("/doctor")

    return render_template("doctor_dashboard.html", appointments=appointments)


@app.route("/doctor/appointments")
@login_required
@role_required("doctor")
def doctor_appointments():
    """List first 50 appointments for the doctor (past, present and future).
    This is a lightweight placeholder and assumes an appointments table exists.
    """
    doctor_id = session.get("user_id")
    try:
        appointments = db.execute(
            """
            SELECT a.appointment_id, p.first_name || ' ' || p.last_name AS patient_name, a.appointment_date AS appointment_time, a.status
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


@app.route("/secretary")
@login_required
@role_required("secretary")
def secretary_dashboard():
    """Secretary main page: truncated list of appointments with all doctors."""
    try:
        appointments = db.execute(
            """
            SELECT a.appointment_id, a.appointment_date AS appointment_time, a.status,
                   p.first_name || ' ' || p.last_name AS patient_name,
                   u.first_name || ' ' || u.last_name AS doctor_name
            FROM appointments a
            JOIN patients p ON a.patient_id = p.patient_id
            JOIN users u ON a.doctor_id = u.user_id
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
    """List employed doctors with a virtual active-appointments column, specialty, and schedule."""
    try:
        doctors = db.execute(
            """
            SELECT u.user_id, u.first_name, u.last_name, u.username,
                   u.start_time, u.end_time, s.name AS specialty,
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
            SELECT a.appointment_id, a.appointment_date AS appointment_time, a.status,
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


@app.route("/secretary/register")
@login_required
@role_required("secretary")
def secretary_register():
    flash("Register appointment form not implemented yet.", "info")
    return redirect("/secretary")


@app.route("/owner/dashboard")
@login_required
@role_required("owner")
def owner_dashboard():
    """Owner analytics dashboard placeholder."""
    return render_template("owner_dashboard.html")


@app.route("/owner/doctors")
@login_required
@role_required("owner")
def owner_doctors():
    try:
        doctors = db.execute(
            """
            SELECT u.user_id, u.first_name, u.last_name, u.username,
                   u.start_time, u.end_time, s.name AS specialty,
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


@app.route("/patients")
@login_required
@role_required(["doctor", "secretary", "owner"])
def patients_list():
    """List patients with full details: first name, last name, cedula, phone and appointment datetime."""
    try:
        patients = db.execute(
            """
            SELECT p.patient_id, p.first_name, p.last_name, p.dni AS cedula, p.phone, a.appointment_date AS appointment_time
            FROM patients p
            LEFT JOIN appointments a ON p.patient_id = a.patient_id
            ORDER BY a.appointment_date DESC
            """
        )
    except Exception as e:
        print(e)
        patients = []

    return render_template("patients_list.html", patients=patients)