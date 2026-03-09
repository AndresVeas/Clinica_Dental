from flask import redirect, session, flash
from functools import wraps
from typing import Iterable


def login_required(f):
    """Require a logged-in user for the wrapped route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def role_required(required_roles):
    """
    Decorator to require one or more user roles.

    Usage:
        @role_required("doctor")
        @role_required(["doctor", "owner"])  # allow multiple roles
    """
    # Normalize to a set for membership checks
    if isinstance(required_roles, str):
        allowed_roles = {required_roles}
    elif isinstance(required_roles, Iterable):
        allowed_roles = set(required_roles)
    else:
        allowed_roles = {str(required_roles)}

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 1. Verify user is logged in
            if session.get("user_id") is None:
                return redirect("/login")

            # 2. Verify user's role is in the allowed set
            current_role = session.get("user_role")
            # sysadmin can access any route (global override)
            if current_role == "sysadmin":
                return f(*args, **kwargs)
            if current_role not in allowed_roles:
                flash("Access denied: insufficient privileges.", "danger")
                return redirect("/")

            return f(*args, **kwargs)

        return decorated_function

    return decorator