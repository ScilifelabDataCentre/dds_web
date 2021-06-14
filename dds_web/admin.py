"Admin page functions"

# Temp solution #

import os
from flask import (
    Blueprint,
    render_template,
    request,
    current_app,
    session,
    redirect,
    url_for,
    make_response,
    jsonify,
)

from dds_web import db
from dds_web.crypt.auth import gen_argon2hash
from dds_web.database import models
from dds_web.database import db_utils
from dds_web.utils import admin_access_required

admin_blueprint = Blueprint("admin", __name__)


@admin_blueprint.route("/", methods=["GET", "POST"])
@admin_access_required
def admin_page():
    """Admin handing"""

    if request.method == "GET":
        users = models.User.query.all()
        facilities = models.Facility.query.all()
        return render_template("admin/admin_home.html", users=users, facilities=facilities)

    elif request.method == "POST":
        task = request.form.get("task")

        # Delete a user
        if task == "delete":
            account_name = request.form.get("account_name")
            user_role = models.Role.query.filter_by(username=account_name).one_or_none()
            if not user_role:
                return make_response(
                    jsonify({"status": 440, "message": "Username do not exist"}), 440
                )
            if user_role.facility == 1:
                account = models.Facility.query.filter_by(username=account_name).one()
                projects = db_utils.get_facilty_projects(
                    db_utils.get_facility_column_by_username(account_name, "public_id")
                )
            else:
                account = models.User.query.filter_by(username=account_name).one()
                projects = db_utils.get_user_projects(
                    db_utils.get_user_column_by_username(account_name, "public_id")
                )
            if projects:
                return make_response(
                    jsonify(
                        {
                            "status": 440,
                            "message": "Account '{}' can't be deleted, have projects".format(
                                account_name
                            ),
                        }
                    ),
                    440,
                )
            account_role = models.Role.query.filter_by(username=account_name).one()
            db.session.delete(account)
            db.session.delete(account_role)
            db.session.commit()
            return make_response(
                jsonify(
                    {
                        "status": 200,
                        "message": "Successfully deleted user '{}'".format(account_name),
                    }
                ),
                200,
            )

        # Add a user
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        is_admin = request.form.get("userType", "") == "admin"
        is_facility = request.form.get("userType", "") == "facility"
        facility_name = request.form.get("facility_name", "")
        facility_ref = request.form.get("facility_ref", "")

        # Validate user fields
        if username == "":
            return make_response(
                jsonify({"status": 400, "message": "Username cannot be blank"}), 400
            )
        if password == "":
            return make_response(
                jsonify({"status": 400, "message": "Password cannot be blank"}), 400
            )
        if not field_uniq(username, "username"):
            return make_response(
                jsonify(
                    {"status": 400, "message": "Username '{}' already exists".format(username)}
                ),
                400,
            )

        if is_facility:
            # Validate facility fields
            if facility_name == "":
                return make_response(
                    jsonify({"status": 400, "message": "Facility name cannot be blank"}), 400
                )
            if facility_ref == "":
                return make_response(
                    jsonify({"status": 400, "message": "Facility reference cannot be blank"}), 400
                )
            if not field_uniq(facility_name, "name"):
                return make_response(
                    jsonify({"status": 400, "message": "Facility name already exists"}), 400
                )
            if not field_uniq(facility_ref, "internal_ref"):
                return make_response(
                    jsonify({"status": 400, "message": "Facility internal ref already exists"}), 400
                )

            public_id = genarate_public_id("Facility")
            acc_obj = models.Facility(
                username=username,
                password=gen_argon2hash(password),
                public_id=public_id,
                name=facility_name,
                internal_ref=facility_ref,
                safespring=current_app.config.get("DDS_SAFE_SPRING_PROJECT"),
            )
        else:
            public_id = genarate_public_id("User")
            acc_obj = models.User(
                username=username,
                password=gen_argon2hash(password),
                admin=is_admin,
                public_id=public_id,
            )
        role_obj = models.Role(username=username, facility=is_facility)

        db.session.add_all([acc_obj, role_obj])
        db.session.commit()
        return make_response(
            jsonify(
                {
                    "status": 200,
                    "message": "Successfully added user '{}'".format(username),
                    "user": {
                        "username": username,
                        "public_id": public_id,
                        "admin": is_admin,
                        "facility_name": facility_name,
                        "facility_ref": facility_ref,
                    },
                }
            ),
            200,
        )


def genarate_public_id(table):
    pub_id = os.urandom(5).hex()
    while pub_id:
        pids = db_utils.get_full_column_from_table(table=table, column="public_id")
        if pub_id not in pids:
            return pub_id


def field_uniq(field, name):
    entries = db_utils.get_full_column_from_table(table="Facility", column=name)
    if name == "username":
        entries.extend(db_utils.get_full_column_from_table(table="User", column=name))
    return field not in entries
