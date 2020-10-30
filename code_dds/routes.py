"""Application routes."""
from datetime import datetime as dt
from flask import request, render_template, make_response, redirect, url_for, session
from flask import current_app as app
from .models import db, User


@app.route("/")
def home():
    """Home page."""
    return render_template("home.html")




