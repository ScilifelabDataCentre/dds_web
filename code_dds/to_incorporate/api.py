"""REST API part"""

import flask
import mariadb
import utils

blueprint = flask.Blueprint('api', __name__)

@blueprint.route('/list_users', methods=['GET'])
def list_users():
    """List users in DB"""
    if utils.is_method_get():
        #make a cursor and execute a command
        cursor = flask.g.db.cursor()
        cursor.execute("SELECT Firstname,Lastname,Username FROM Users")
        
        #Collect the users as list of dict
        udict = {}
        for f, l, u in cursor:
            udict[u] = {'firstname': f, 'lastname': l, 'username': u}
        
        return udict

@blueprint.route('/get_user', methods=['GET'])
def get_user():
    """Get a user from DB by userid"""
    if utils.is_method_get():
        #Check if required arg exists
        try:
            username = flask.request.args['username']
        except Exception as e:
            print(e)
            return "No valid username provided"
            
        #make a cursor and execute a command
        cursor = flask.g.db.cursor()
        cursor.execute("SELECT Firstname,Lastname,Username FROM Users WHERE Username=?", (username,))
        
        for f, l, u in cursor:
            return {'firstname': f, 'lastname': l, 'username': u}


