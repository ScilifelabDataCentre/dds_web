"User display and login/logout HTMl endpoints."

import flask
from flask import render_template, request, current_app, session, redirect, url_for, jsonify
import sqlalchemy

from dds_web import timestamp, oauth
from dds_web.api.login import ds_access
from dds_web.crypt.auth import validate_user_credentials
from dds_web.database import models
from dds_web.database import db_utils
from dds_web.utils import login_required

# temp will be removed in next version
from dds_web.development import cache_temp as tc

user_blueprint = flask.Blueprint("user", __name__)


@user_blueprint.route("/login", methods=["GET", "POST"])
def login():
    """Login to a user account"""

    if request.method == "GET":
        if session.get("is_admin"):
            return redirect(url_for("admin.admin_page"))
        elif session.get("current_user") and session.get("usid"):
            return redirect(url_for("user.user_page", loginname=session["current_user"]))
        else:
            return render_template("user/login.html", next=request.args.get("next"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        credentials_validated, is_facility, message, user_info = validate_user_credentials(
            username, password
        )
        if not credentials_validated:
            return render_template(
                "user/login.html", next=request.form.get("next"), login_error_message=message
            )
        session["current_user"] = user_info["username"]
        session["current_user_id"] = user_info["id"]
        session["is_admin"] = user_info.get("admin", False)
        session["is_facility"] = is_facility
        session["facility_name"] = user_info.get("facility_name")
        session["facility_id"] = user_info.get("facility_id")
        # temp admin fix
        if session["is_admin"]:
            return redirect(url_for("admin.admin_page"))
        # temp should be removed in next version
        import os

        usid = os.urandom(3).hex()
        session["usid"] = usid
        tc.store_temp_ucache(username, password, usid)
        if request.form.get("next"):
            to_go_url = request.form.get("next")
        else:
            to_go_url = url_for("user.user_page", loginname=request.form.get("username"))
        return redirect(to_go_url)


def do_login(session, identifier: str, password: str = "") -> bool:
    """
    Check if a user with matching identifier exists. If so, log in as that user.

    TODO:
      * Add support for passwords

    Args:
        session: The Flask session to use.
        identifer (str): User identifier to use for login.
        password (str): Password in case a password is used for the login.

    Returns:
        bool: Whether the login attempt succeeded.
    """
    try:
        account = models.Identifier.query.filter(models.Identifier.identifier == identifier).first()
    except sqlalchemy.exc.SQLAlchemyError:
        return False
    user_info = account.user
    # Use the current login definitions for compatibility
    session["current_user"] = user_info.username
    session["current_user_id"] = user_info.id
    session["is_admin"] = user_info.role == "admin"
    session["is_facility"] = user_info.role == "facility"
    if session["is_facility"]:
        facility_info = models.Facility.query.filter(
            models.Facility.id == account.facility_id
        ).first()

        session["facility_name"] = facility_info.name
        session["facility_id"] = facility_info.id
    return True


@user_blueprint.route("/login-oidc")
def oidc_login():
    """Perform a login using OpenID Connect (e.g. Elixir AAI)."""
    client = oauth.create_client("default_login")
    if not client:
        return flask.Response(status=404)
    redirect_uri = flask.url_for("user.oidc_authorize", _external=True)
    return client.authorize_redirect(redirect_uri)


@user_blueprint.route("/login-oidc/authorize")
def oidc_authorize():
    """Authorize a login using OpenID Connect (e.g. Elixir AAI)."""
    client = oauth.create_client("default_login")
    token = client.authorize_access_token()
    if "id_token" in token:
        user_info = client.parse_id_token(token)
    else:
        user_info = client.userinfo()

    if do_login(flask.session, user_info["email"]):
        flask.current_app.logger.info(f"Passed login attempt")
        return flask.redirect(flask.url_for("home"))
    else:
        return flask.abort(status=403)


@user_blueprint.route("/logout", methods=["GET"])
def logout():
    """Logout of a user account"""
    # temp should be removed in next version
    tc.clear_temp_ucache(session.get("current_user"), session.get("usid"))
    session.pop("current_user", None)
    session.pop("current_user_id", None)
    session.pop("is_facility", None)
    session.pop("is_admin", None)
    session.pop("facility_name", None)
    session.pop("facility_id", None)
    session.pop("usid", None)
    return redirect(url_for("home"))


@user_blueprint.route("/<loginname>", methods=["GET"])
@login_required
def user_page(loginname=None):
    """User home page"""
    # return session
    if session.get("is_admin"):
        return redirect(url_for("admin.admin_page"))
    if session["is_facility"]:
        projects_list = db_utils.get_facilty_projects(fid=session["facility_id"])
    else:
        projects_list = db_utils.get_user_projects(uid=session["current_user_id"])
    # TO DO: change dbfunc passing in future
    return render_template(
        "project/list_project.html",
        projects_list=projects_list,
        dbfunc=db_utils.get_facility_column,
        timestamp=timestamp,
    )

# @user_blueprint.route("/signup", methods=["GET", "POST"])
# def signup():
#     """Signup a user account"""
#
#     if request.method == "GET":
#         return render_template('user/signup.html', title='Signup')
#     if request.method == "POST":
#         pass

@user_blueprint.route("/account")
@login_required
def account_info():
    """User account page"""

    return render_template("user/account.html")


# TO DO: MAYBE MOVE THIS TO THE API (OR KEEP IT HERE IF API IS ONLY FOR CLI)
@user_blueprint.route("/test", methods=["GET", "POST", "PUT", "DELETE"])
@login_required
def account_test():
    """account page"""
    username=session["current_user"]
    if request.method == "POST":
        # new email
        pass
    if request.method == "DELETE":
        # delete email
        pass
    if request.method == "PUT":
        # update name
        pass
    if request.method == "GET":

        account_info = {}
        account_info['username'] = username
        account_info['permissions'] = db_utils.get_user_column_by_username(username, 'permissions')
        account_info['first_name'] = None #db_utils.get_user_column_by_username(username, 'first_name')
        account_info['last_name'] =  None #db_utils.get_user_column_by_username(username, 'last_name')
        account_info["emails"] = [{"address": "userX@email1.com", "primary": False}, {"address": "userX@email2.com", "primary": True}]

        account_info["emails"] = sorted(account_info["emails"],
                                    key=lambda k: k['primary'],
                                    reverse=True)
        # permissions_dict = {"get": "g", "ls": "l", "put": "p", "rm": "r"}
        #     if permissions_dict[args["method"]] not in list(current_user.permissions):

        return account_info


# @account_blueprint.route("/test")
# def account_test(loginname=None):
#     """account page"""

#     username=session["current_user"]

#     account_info = {
#             'username': username,
#             'emails': [], #[{"address": "userX@email1.com", "primary": False}, {"address": "userX@email2.com", "primary": True}]
#             'permissions': None,
#             'first_name': None,
#             'last_name': None
#         }

#     for info in account_info:
#         if info != "username" or info !="emails":
#             try:
#                 # TO DO: change to db.one_or_none()
#                 account_info[info] = db_utils.get_user_column_by_username(username, info)
#             except:
#                 pass
#         if info == "emails":
#             user_info_list = models.User.query.filter_by(username=username).all()
#             account_info["emails"] = [
#                 {'address': getattr(user_row, "email", None),
#                 'primary': getattr(user_row, "primary", False)}
#                 for user_row in user_info_list
#             ]

#     account_info["emails"] = sorted(account_info["emails"],
#                                     key=lambda k: k['primary'],
#                                     reverse=True)

#     return json.dumps(account_info)




# class UserAccount(flask_restful.Resource):
#     #method_decorators = [token_required]
#     def get(self):
#         # token = flask.response.json()
#         # if "token" in token:
#         #     a=True
#         # else:
#         #     a=False
#         account_info = {}
#         account_info['username'] = flask.session["current_user"]
#         account_info['permissions'] = db_utils.get_user_column_by_username(flask.session["current_user"], 'permissions')
#         account_info['first_name'] = None #db_utils.get_user_column_by_username(username, 'first_name')
#         account_info['last_name'] =  args #db_utils.get_user_column_by_username(username, 'last_name')
#         account_info["emails"]
#         if flask.session.get("current_user") and flask.session.get("usid"):
#             args = flask.request.args
#             account_info['username'] = flask.session["current_user"]
#             account_info['permissions'] = db_utils.get_user_column_by_username(flask.session["current_user"], 'permissions')
#             account_info['first_name'] = None #db_utils.get_user_column_by_username(username, 'first_name')
#             account_info['last_name'] =  args #db_utils.get_user_column_by_username(username, 'last_name')
#             account_info["emails"] = [
#                 {'address': "email",
#                 'primary': False}
#             ]

        # username=session["current_user"]

        # account_info = {}
        # account_info['username'] = username
        # account_info['permissions'] = db_utils.get_user_column_by_username(username, 'permissions')
        # account_info['first_name'] = None #db_utils.get_user_column_by_username(username, 'first_name')
        # account_info['last_name'] =  None #db_utils.get_user_column_by_username(username, 'last_name')

        # user_info_list = models.User.query.filter_by(username=username).all()
        # account_info["emails"] = [
        #     {'address': getattr(user_row, "email", None),
        #     'primary': getattr(user_row, "primary", False)}
        #     for user_row in user_info_list
        # ]
        # account_info["emails"] = sorted(account_info["emails"],
        #                                 key=lambda k: k['primary'],
        #                                 reverse=True)

        # return account_info
        # [permission.value for permission in permissions if permission.key in permissions]
        # Deny access if project or method not specified
        # args = flask.request.args
        # if "method" not in args:
        #     app.logger.debug("No method in request.")
        #     return flask.make_response("Invalid request.", 500)

        # permissions_dict = {"get": "g", "ls": "l", "put": "p", "rm": "r"}
        # if permissions_dict[args["method"]] not in list(current_user.permissions):
        #     return flask.make_response(
        #         f"Attempted to '{args['method']}' in project '{project['id']}'. Permission denied.",
        #         401,
        #     )

        # # app.logger.debug("Updating token...")
        # # token, error = jwt_token(
        # #     username=current_user.username,
        # #     project_id=project["id"],
        # #     project_access=True,
        # #     permission=args["method"],
        # # )
        # # if token is None:
        # #     return flask.make_response(error, 500)

        # # # Project access granted
        # # return flask.jsonify(
        # #     {
        # #         "dds-access-granted": True,
        # #         "token": token.decode("UTF-8"),
        # #     }
        # # )
        # #         # Project access denied
        # # return flask.make_response("Project access denied", 401)

        # # # Project access denied
        # # return flask.make_response("Project access denied", 401)
    # def get(self, current_user, project, *args):
    #     """Get info regarding all projects which user is involved in."""

    #     if project["permission"] != "ls":
    #         return flask.make_response(
    #             f"User {current_user.username} does not have permission to view projects.", 401
    #         )

    #     # TODO: Return different things depending on if facility or not
    #     columns = ["Project ID", "Title", "PI", "Status", "Last updated"]
    #     all_projects = [
    #         {
    #             columns[0]: x.public_id,
    #             columns[1]: x.title,
    #             columns[2]: x.pi,
    #             columns[3]: x.status,
    #             columns[4]: timestamp(
    #                 datetime_string=x.date_updated if x.date_updated else x.date_created
    #             ),
    #         }
    #         for x in current_user.projects
    #     ]
    #     app.logger.debug(all_projects)
    #     return flask.jsonify({"all_projects": all_projects, "columns": columns})
    # def put(self, current_user, *args):
    #     pass
    # def put(self, _, project):
    #     """Update the project size and updated time stamp."""

    #     updated, error = (False, "")
    #     current_try, max_tries = (1, 5)
    #     while current_try < max_tries:
    #         try:
    #             current_project = models.Project.query.filter(
    #                 models.Project.public_id == func.binary(project["id"])
    #             ).first()

    #             tot_file_size = (
    #                 models.File.query.with_entities(
    #                     sqlalchemy.func.sum(models.File.size_original).label("sizeSum")
    #                 )
    #                 .filter(models.File.project_id == current_project.id)
    #                 .first()
    #             )

    #             current_project.size = tot_file_size.sizeSum
    #             current_project.date_updated = timestamp()
    #             db.session.commit()
    #         except sqlalchemy.exc.SQLAlchemyError as err:
    #             error = str(err)
    #             db.session.rollback()
    #             current_try += 1
    #         else:
    #             updated = True
    #             break

    #     return flask.jsonify({"updated": updated, "error": error, "tries": current_try})
    # def post(self, current_user, *args):
    #     pass
        # def post(self, _, project):
        # """Add new file to DB"""

        # message = ""
        # required_info = [
        #     "name",
        #     "name_in_bucket",
        #     "subpath",
        #     "size",
        #     "size_processed",
        #     "compressed",
        #     "salt",
        #     "public_key",
        #     "checksum",
        # ]
        # args = flask.request.args
        # if not all(x in args for x in required_info):
        #     missing = [x for x in required_info if x not in args]
        #     return flask.make_response(
        #         f"Information missing ({missing}), cannot add file to database.", 500
        #     )

        # try:
        #     current_project = models.Project.query.filter(
        #         models.Project.public_id == func.binary(project["id"])
        #     ).first()

        #     # Check if file already in db
        #     existing_file = (
        #         models.File.query.filter(
        #             sqlalchemy.and_(
        #                 models.File.name == func.binary(args["name"]),
        #                 models.File.project_id == func.binary(current_project.id),
        #             )
        #         )
        #         .with_entities(models.File.id)
        #         .first()
        #     )

        #     if existing_file or existing_file is not None:
        #         return flask.make_response(
        #             f"File '{args['name']}' already exists in the database!", 500
        #         )

        #     # Add new file to db
        #     new_file = models.File(
        #         public_id=os.urandom(16).hex(),
        #         name=args["name"],
        #         name_in_bucket=args["name_in_bucket"],
        #         subpath=args["subpath"],
        #         size_original=args["size"],
        #         size_stored=args["size_processed"],
        #         compressed=bool(args["compressed"] == "True"),
        #         salt=args["salt"],
        #         public_key=args["public_key"],
        #         time_uploaded=timestamp(),
        #         checksum=args["checksum"],
        #         project_id=current_project,
        #     )
        #     current_project.files.append(new_file)
        #     db.session.add(new_file)
        #     db.session.commit()
        # except sqlalchemy.exc.SQLAlchemyError as err:
        #     app.logger.debug(err)
        #     db.session.rollback()
        #     return flask.make_response(
        #         f"Failed to add new file '{args['name']}' to database: {err}", 500
        #     )

        # return flask.jsonify({"message": f"File '{args['name']}' added to db."})
    # def delete(self, current_user, *args):
    #     pass
        # """Removes all project contents."""

        # # Delete files
        # removed, error = (False, "")
        # with DBConnector() as dbconn:
        #     removed, error = dbconn.delete_all()

        #     # Return error if contents not deleted from db
        #     if not removed:
        #         return flask.make_response(error, 500)

        #     # Delete from bucket
        #     with ApiS3Connector() as s3conn:
        #         if None in [s3conn.url, s3conn.keys, s3conn.bucketname]:
        #             return flask.make_response("No s3 info returned! " + s3conn.message, 500)

        #         removed, error = s3conn.remove_all()

        #         # Return error if contents not deleted from s3 bucket
        #         if not removed:
        #             db.session.rollback()
        #             return flask.make_response(error, 500)

        #         # Commit changes to db
        #         try:
        #             db.session.commit()
        #         except sqlalchemy.exc.SQLAlchemyError as err:
        #             return flask.make_response(str(err), 500)

        # return flask.jsonify({"removed": removed, "error": error})


