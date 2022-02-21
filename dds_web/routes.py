"""Application routes."""
from flask import render_template
from flask import current_app as app


@app.route("/")
def home():
    """Home page."""
    return render_template("home.html")


@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template("404.html"), 404
