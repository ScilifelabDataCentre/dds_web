"""Application routes."""
from flask import render_template
from flask import current_app as app

@app.route("/")
def home():
    """Home page."""
    return render_template("home.html")

