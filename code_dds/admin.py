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
    jsonify
    )

from code_dds import db
from code_dds.crypt.auth import gen_argon2hash
from code_dds.db_code import models
from code_dds.db_code import db_utils
from code_dds.utils import admin_access_required

admin_blueprint = Blueprint("admin", __name__)

@admin_blueprint.route("/", methods=["GET", "POST"])
@admin_access_required
def admin_page():
    """Admin handing"""
    
    if request.method == "GET":
        users = models.User.query.all()
        facilities = models.Facility.query.all()
        return render_template('admin/admin_home.html', users=users, facilities=facilities)
        
    elif request.method == "POST":
        task = request.form.get("task")
        if task == "delete":
            account_name = request.form.get("account_name")
            user_role = models.Role.query.filter_by(username=account_name).one_or_none()
            if not user_role:
                return make_response(jsonify({"status": 440, "message": "Username do not exist"}), 440)
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
                return make_response(jsonify({"status": 440, "message": "Account can't be deleted, have projects"}), 440)
            account_role = models.Role.query.filter_by(username=account_name).one()
            db.session.delete(account)
            db.session.delete(account_role)
            db.session.commit()
            return make_response(jsonify({"status": 200, "message": "Successfully deleted user '{}'".format(account_name)}), 200)
            
        
        username = request.form.get("username")
        password = request.form.get("password")
        is_admin = True if request.form.get("is_admin") else False
        is_facility = True if request.form.get("is_facility") else False
        facility_name = request.form.get("facility_name")
        facility_ref = request.form.get("facility_ref")
        
        if not field_uniq(username, "username"):
            return make_response(jsonify({"status": 440, "message": "Username already exists"}), 440)
        
        if is_facility:
            if not field_uniq(facility_name, "name"):
                return make_response(jsonify({"status": 440, "message": "Facility name already exists"}), 440)
            if not field_uniq(facility_ref, "internal_ref"):
                return make_response(jsonify({"status": 440, "message": "Facility internal ref already exists"}), 440)
                
            acc_obj = models.Facility(
                username = username,
                password = gen_argon2hash(password),
                public_id = genarate_public_id("Facility"),
                name = facility_name,
                internal_ref= facility_ref,
                safespring = current_app.config.get("DDS_SAFE_SPRING_PROJECT")
            )
        else:
            acc_obj = models.User(
                username = username,
                password = gen_argon2hash(password),
                admin = is_admin,
                public_id = genarate_public_id("User")
            )
        role_obj = models.Role(username=username, facility=is_facility)
        
        db.session.add_all([acc_obj, role_obj])
        db.session.commit()
        return make_response(jsonify({"status": 200, "message": "Successfully added user '{}'".format(username)}), 200)
        

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
    return (field not in entries)
    
    
