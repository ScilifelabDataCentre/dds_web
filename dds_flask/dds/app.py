"""Main caller script"""

from flask import Flask, g, render_template

import api
import config
import mariadb
import user
import utils

app = Flask(__name__)

config.configit(app)

#  import pdb; pdb.set_trace()


@app.context_processor
def global_template_context():
    """Add functions to be available in template context"""
    return dict(get_csrf_token=utils.get_csrf_token)


@app.before_request
def prepare():
    """Do the neccesary prerequest tasks"""
    g.current_user = "tester"
    g.db = mariadb.connect(**app.config['DB'])


@app.route('/')
def home():
    """Home Page"""
    return render_template('home.html')


@app.route('/login')
def login():
    """Login"""
    return render_template('home.html')


# Register blueprints for URL mapping
app.register_blueprint(user.blueprint, url_prefix='/user')
app.register_blueprint(api.blueprint, url_prefix="/api/v1")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
