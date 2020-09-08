"User display and login/logout HTMl endpoints."

import http.client
import json
import re

from flask import (Blueprint, render_template,
                   request, session, redirect, url_for, g, current_app)
# import flask_mail
from werkzeug.security import check_password_hash, generate_password_hash

from code_dds import constants
from code_dds import utils

KEYS = ["ID", "Firstname", "Lastname", "Username", "Password", "Settings",
        "Email", "Phone"]

blueprint = Blueprint("user", __name__, url_prefix="/user")


@blueprint.route("/login", methods=["GET", "POST"])
def login():
    """Login to a user account.
    Creates the admin user specified in the settings.json, if not done.
    """

    if request.method == "GET":
        # if utils.http_GET():
        return render_template('login.html', title='Login')
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        token = session.get("_csrf_token", None)
        return f"email: {email}, password: {password}, csrf: {token}, {token == session.get('_csrf_token')}"
        # try:
        #     if username and password:
        #         do_login(username, password)
        #     else:
        #         raise ValueError
        #     try:
        #         next = request.form["next"]
        #     except KeyError:
        #         return redirect(url_for("home"))
        #     else:
        #         return redirect(next)
        # except ValueError:
        #     utils.flash_error("Invalid user or password, or account disabled.")
        #     return redirect(url_for(".login"))

    # app = current_app

    # if app.config.get("ADMIN_USER"):
    #     user = get_user(username=app.config["ADMIN_USER"]["username"])
    #     if user is None:
    #         try:
    #             with UserSaver() as saver:
    #                 saver.set_username(app.config["ADMIN_USER"]["username"])
    #                 saver.set_email(app.config["ADMIN_USER"]["email"])
    #                 saver.set_role(constants.ADMIN)
    #                 saver.set_status(constants.ENABLED)
    #                 saver.set_password(app.config["ADMIN_USER"]["password"])
    #             utils.get_logger().info("Created admin user " +
    #                                     app.config["ADMIN_USER"]["username"])
    #         except ValueError as error:
    #             utils.get_logger().error("Could not create admin user;"
    #                                      " misconfiguration.")


# @blueprint.route("/logout", methods=["POST"])
# def logout():
#     "Logout from the user account."
#     username = session.pop("username", None)
#     if username:
#         utils.get_logger().info(f"logged out {username}")
#     return redirect(url_for("home"))


# @blueprint.route("/register", methods=["GET", "POST"])
# def register():
#     "Register a new user account."
#     if utils.http_GET():
#         return render_template("user/register.html")

#     elif utils.http_POST():
#         try:
#             with UserSaver() as saver:
#                 saver.set_username(request.form.get("username"))
#                 saver.set_email(request.form.get("email"))
#                 saver.set_role(constants.USER)
#                 if g.am_admin:
#                     password = request.form.get("password") or None
#                     if password:
#                         confirm = request.form.get("confirm_password")
#                         if password != confirm:
#                             raise ValueError("Password differs from"
#                                              " confirmed password.")
#                     saver.set_password(password)
#                     saver.set_status(constants.ENABLED)
#                 elif not current_app.config["MAIL_SERVER"]:
#                     password = request.form.get("password") or None
#                     if password:
#                         confirm = request.form.get("confirm_password")
#                         if password != confirm:
#                             raise ValueError("Password an confirmed password"
#                                              " not the same.")
#                     saver.set_password(password)
#                 else:
#                     saver.set_password()
#             user = saver.doc
#         except ValueError as error:
#             utils.flash_error(error)
#             return redirect(url_for(".register"))
#         utils.get_logger().info(f"registered user {user['username']}")
#         # Directly enabled.
#         if user["status"] == constants.ENABLED:
#             if user["password"][:5] == "code:":
#                 utils.get_logger().info(f"enabled user {user['username']}")
#                 # Send code by email to user.
#                 if current_app.config["MAIL_SERVER"]:
#                     send_password_code(user, "registration")
#                     utils.flash_message(
#                         "User account created; check your email.")
#                 # No email server: must contact admin.
#                 else:
#                     utils.flash_message("User account created; contact"
#                                         " the site admin to get the password"
#                                         " setting code.")
#             # Directly enabled and password set. No email to anyone.
#             else:
#                 utils.get_logger().info(f"enabled user {user['username']}"
#                                         " and set password")
#                 utils.flash_message("User account created and password set.")
#         # Was set to 'pending'; send email to admins if email server defined.
#         elif current_app.config["MAIL_SERVER"]:
#             admins = get_users(constants.ADMIN, status=constants.ENABLED)
#             emails = [u["email"] for u in admins]
#             site = current_app.config["SITE_NAME"]
#             message = flask_mail.Message(f"{site} user account pending",
#                                          recipients=emails)
#             url = utils.url_for(".display", username=user["username"])
#             message.body = f"To enable the user account, go to {url}"
#             utils.mail.send(message)
#             utils.get_logger().info(f"pending user {user['username']}")
#             utils.flash_message("User account created; an email will be sent"
#                                 " when it has been enabled by the admin.")
#         else:
#             utils.get_logger().info(f"pending user {user['username']}")
#             utils.flash_message("User account created; admin will enable it"
#                                 " at some point. Try login later.")
#         return redirect(url_for("home"))


# @blueprint.route("/reset", methods=["GET", "POST"])
# def reset():
#     "Reset the password for a user account and send email."
#     if not current_app.config["MAIL_SERVER"]:
#         utils.flash_error("Cannot reset password; no email server defined.")
#         return redirect(url_for("home"))

#     if utils.http_GET():
#         email = request.args.get("email") or ""
#         email = email.lower()
#         return render_template("user/reset.html", email=email)

#     elif utils.http_POST():
#         try:
#             user = get_user(email=request.form["email"])
#             if user is None:
#                 raise KeyError
#             if user["status"] != constants.ENABLED:
#                 raise KeyError
#         except KeyError:
#             pass
#         else:
#             with UserSaver(user) as saver:
#                 saver.set_password()
#             send_password_code(user, "password reset")
#         utils.get_logger().info(f"reset user {user['username']}")
#         utils.flash_message(
#             "An email has been sent if the user account exists.")
#         return redirect(url_for("home"))


@blueprint.route("/password", methods=["GET", "POST"])
def password():
    "Set the password for a user account, and login user."
    if utils.http_GET():
        return render_template(
            "user/password.html",
            username=request.args.get("username"),
            code=request.args.get("code"))

    elif utils.http_POST():
        try:
            code = ""
            try:
                username = request.form.get("username") or ""
                if not username:
                    raise ValueError
                user = get_user(username=username)
                if user is None:
                    raise ValueError
                if g.am_admin and \
                   g.current_user["username"] != username:
                    pass        # No check for either code or current password.
                elif current_app.config["MAIL_SERVER"]:
                    code = request.form.get("code") or ""
                    if user["password"] != f"code:{code}":
                        raise ValueError
                else:
                    password = request.form.get("current_password") or ""
                    if not check_password_hash(user["password"], password):
                        raise ValueError
            except ValueError:
                if current_app.config["MAIL_SERVER"]:
                    raise ValueError("No such user or wrong code.")
                else:
                    raise ValueError("No such user or wrong password.")
            password = request.form.get("password") or ""
            if len(password) < current_app.config["MIN_PASSWORD_LENGTH"]:
                raise ValueError("Too short password.")
            if not current_app.config["MAIL_SERVER"]:
                if password != request.form.get("confirm_password"):
                    raise ValueError("Wrong password entered; confirm failed.")
        except ValueError as error:
            utils.flash_error(str(error))
            return redirect(url_for(".password",
                                    username=username,
                                    code=code))
        else:
            with UserSaver(user) as saver:
                saver.set_password(password)
            utils.get_logger().info(f"password user {user['username']}")
            if not g.current_user:
                do_login(username, password)
        return redirect(url_for("home"))


@blueprint.route("/display/<name:username>")
@utils.login_required
def display(username):
    "Display the given user."
    user = get_user(username=username)
    if user is None:
        utils.flash_error("No such user.")
        return redirect(url_for("home"))
    if not am_admin_or_self(user):
        utils.flash_error("Access not allowed.")
        return redirect(url_for("home"))
    return render_template("user/display.html", user=user)


@blueprint.route("/display/<name:username>/edit",
                 methods=["GET", "POST", "DELETE"])
@utils.login_required
def edit(username):
    "Edit the user display. Or delete the user."
    user = get_user(username=username)
    if user is None:
        utils.flash_error("No such user.")
        return redirect(url_for("home"))
    if not am_admin_or_self(user):
        utils.flash_error("Access not allowed.")
        return redirect(url_for("home"))

    if utils.http_GET():
        return render_template("user/edit.html",
                               user=user,
                               change_role=am_admin_and_not_self(user),
                               deletable=is_empty(user))

    elif utils.http_POST():
        with UserSaver(user) as saver:
            if g.am_admin:
                email = request.form.get("email")
                if email != user["email"]:
                    saver.set_email(email)
            if am_admin_and_not_self(user):
                saver.set_role(request.form.get("role"))
            if request.form.get("apikey"):
                saver.set_apikey()
        return redirect(
            url_for(".display", username=user["username"]))

    elif utils.http_DELETE():
        if not is_empty(user):
            utils.flash_error("Cannot delete non-empty user account.")
            return redirect(url_for(".display", username=username))
        with g.db:
            g.db.execute(
                "DELETE FROM logs WHERE docid=?", (user["iuid"],))
            g.db.execute(
                "DELETE FROM users WHERE username=?", (username,))
        utils.flash_message(f"Deleted user {username}.")
        utils.get_logger().info(f"deleted user {username}")
        if g.am_admin:
            return redirect(url_for(".all"))
        else:
            return redirect(url_for("home"))


@blueprint.route("/display/<name:username>/logs")
@utils.login_required
def logs(username):
    "Display the log records of the given user."
    user = get_user(username=username)
    if user is None:
        utils.flash_error("No such user.")
        return redirect(url_for("home"))
    if not am_admin_or_self(user):
        utils.flash_error("Access not allowed.")
        return redirect(url_for("home"))
    return render_template(
        "logs.html",
        title=f"User {user['username']}",
        cancel_url=url_for(".display", username=user["username"]),
        api_logs_url=url_for("api_user.logs", username=user["username"]),
        logs=utils.get_logs(user["iuid"]))


@blueprint.route("/all")
@utils.admin_required
def all():
    "Display list of all users."
    return render_template("user/all.html", users=get_users())


# Utility functions


def get_user(username=None, email=None, apikey=None):
    """Return the user for the given username, email or apikey.
    Return None if no such user.
    """
    sql = f"SELECT {','.join(KEYS)} FROM Users"
    cursor = g.db.cursor()
    if username:
        cursor.execute(sql + " WHERE Username=?", (username,))
    elif email:
        cursor.execute(sql + " WHERE Email=?", (email.lower(),))
    # elif apikey:
    #     cursor.execute(sql + " WHERE apikey=?", (apikey,))
    else:
        return None
    rows = list(cursor)
    if len(rows) == 0:
        return None
    else:
        return dict(zip(rows[0].keys(), rows[0]))


def get_users(role=None, status=None):
    "Get the users optionally specified by role and status."
    assert role is None or role in constants.USER_ROLES
    assert status is None or status in constants.USER_STATUSES
    cursor = g.db.cursor()
    if role is None:
        rows = cursor.execute(f"SELECT {','.join(KEYS)} FROM users")
    elif status is None:
        rows = cursor.execute(f"SELECT {','.join(KEYS)} FROM users"
                              " WHERE role=?", (role,))
    else:
        rows = cursor.execute(f"SELECT {','.join(KEYS)} FROM users"
                              " WHERE role=? AND status=?", (role, status))
    return [dict(zip(row.keys(), row)) for row in rows]


def get_current_user():
    """Return the user for the current session.
    Return None if no such user, or disabled.
    """
    user = get_user(username=session.get("username"),
                    apikey=request.headers.get("x-apikey"))
    if user is None or user["status"] != constants.ENABLED:
        session.pop("username", None)
        return None
    return user


def do_login(email, password):
    """Set the session cookie if successful login.
    Raise ValueError if some problem.
    """
    user = get_user(email=email)
    if user is None:
        raise ValueError
    if not check_password_hash(user["Password"], password):
        raise ValueError
    # if user["status"] != constants.ENABLED:
    #     raise ValueError
    session["username"] = user["Username"]
    session.permanent = True
    utils.get_logger().info(f"logged in {user['Username']}")


# def send_password_code(user, action):
#     "Send an email with the one-time code to the user's email address."
#     site = current_app.config["SITE_NAME"]
#     message = flask_mail.Message(f"{site} user account {action}",
#                                  recipients=[user["email"]])
#     url = utils.url_for(".password",
#                         username=user["username"],
#                         code=user["password"][len("code:"):])
#     message.body = f"To set your password, go to {url}"
#     utils.mail.send(message)


def is_empty(user):
    "Is the given user account empty? No data associated with it."
    # XXX Needs implementation.
    return True


def am_admin_or_self(user):
    "Is the current user admin, or the same as the given user?"
    if not g.current_user:
        return False
    if g.am_admin:
        return True
    return g.current_user["username"] == user["username"]


def am_admin_and_not_self(user):
    "Is the current user admin, but not the same as the given user?"
    if g.am_admin:
        return g.current_user["username"] != user["username"]
    return False
