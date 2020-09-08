from flask import Blueprint, g
from flask_restful import Resource, Api


names = {
    "tim": {"age": 19, "gender": "male"},
    "bill": {"age": 70, "gender": "male"},
    "ina": {"age": 29, "gender": "female"}
}


class Login(Resource):
    def get(self):
        try:
            cur = g.db.cursor()
        except:
            pass
        else:
            cur.execute("SELECT Firstname,Lastname,Username FROM Users")

            # Collect the users as list of dict
            udict = {}
            for f, l, u in cur:
                udict[u] = {'firstname': f, 'lastname': l, 'username': u}

            return udict
        # for (ID, Firstname, Lastname, Username, Password, Settings, Email, Phone) in cur:
        #     result[ID] = {"firstname": Firstname,
        #                   "lastname": Lastname,
        #                   "password": Password,
        #                   "settings": Settings,
        #                   "email": Email,
        #                   "phone": Phone}

        return result


user_api = Blueprint('user_api', __name__)
api = Api(user_api)
api.add_resource(Login, "/login", endpoint="login")
