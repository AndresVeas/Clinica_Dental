from flask import redirect, session, flash
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def role_required(required_role):
    """
    Decorate routes to require a specific user role.
    Example: @role_required("doctor")
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 1. Check if the user is logged in
            if session.get("user_id") is None:
                return redirect("/login")
            
            # 2. Check if the user's role matches the required role
            # Ensure you set session["user_role"] during the login process
            current_role = session.get("user_role")
            
            if current_role != required_role:
                # If role doesn't match, show a warning and redirect
                flash(f"Access Denied: This area is restricted to {required_role}s only.", "danger")
                return redirect("/")
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator