""" User related functions """

import flask
import utils

blueprint = flask.Blueprint('user', __name__)

@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    """User login handler"""
    if utils.is_method_get():
        return flask.render_template('user/login.html')