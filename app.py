from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from helper import login_required
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQL("sqlite:///dentist.db")

@app.route("/")
@login_required
def index():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
    else:
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
        session["user_role"] = rows[0]["role_name"] # Stores 'owner', 'doctor', or 'secretary'

        # Redirect user to home page
        flash(f"Welcome back, {rows[0]['first_name']}!", "success")
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