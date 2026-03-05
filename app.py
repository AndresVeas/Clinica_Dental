from flask import Flask, render_template, request, redirect
import cs50

db = get_db

app = Flask(__name__)


@app.route("/")
def index():
    return "<h1>¡El sistema dental está vivo!</h1>"