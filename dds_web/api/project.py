"""Project module."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard Library
import http

# Installed
import flask_restful
import flask
import sqlalchemy
import datetime
import botocore
import marshmallow

# Own modules
import dds_web.utils
from dds_web import auth, db
from dds_web.database import models
from dds_web.api.api_s3_connector import ApiS3Connector
from dds_web.api.dds_decorators import (
    logging_bind_request,
    dbsession,
    json_required,
    handle_validation_errors,
)
from dds_web.errors import (
    AccessDeniedError,
    DDSArgumentError,
    DatabaseError,
    EmptyProjectException,
    DeletionError,
    BucketNotFoundError,
    KeyNotFoundError,
    S3ConnectionError,
    NoSuchUserError,
)
from dds_web.api.user import AddUser
from dds_web.api.schemas import project_schemas, user_schemas
from dds_web.security.project_user_keys import obtain_project_private_key, share_project_private_key
from dds_web.security.auth import get_user_roles_common
from dds_web.api.files import check_eligibility_for_deletion

####################################################################################################
# ENDPOINTS ############################################################################ ENDPOINTS #
####################################################################################################
class ProjectStatus(flask_restful.Resource):
    """Get and update Project status"""

    @auth.login_required
    @logging_bind_request
    @handle_validation_errors
    def get(self):
        """Get current project status and optionally entire status history"""
        # Verify project ID and access
        project = project_schemas.ProjectRequiredSchema().load(flask.request.args)

        # Get current status and deadline
        return_info = {"current_status": project.current_status}
        if project.current_deadline:
            return_info["current_deadline"] = project.current_deadline

        # Get status history
        json_input = flask.request.json
        if json_input and json_input.get("history"):
            history = []
            for pstatus in project.project_statuses:
                history.append(tuple((pstatus.status, pstatus.date_created)))
            history.sort(key=lambda x: x[1], reverse=True)
            return_info.update({"history": history})

        return return_info

    @auth.login_required(role=["Unit Admin", "Unit Personnel"])
    @logging_bind_request
    @json_required
    @handle_validation_errors
    def post(self):
        """Update Project Status."""
        # Verify project ID and access
        project = project_schemas.ProjectRequiredSchema().load(flask.request.args)

        # Check if valid status
        json_input = flask.request.json
        new_status = json_input.get("new_status")
        if not new_status:
            raise DDSArgumentError(message="No status transition provided. Specify the new status.")

        # Override default to send email
        send_email = json_input.get("send_email", True)

        # Initial variable definition
        curr_date = dds_web.utils.current_time()
        delete_message = ""
        is_aborted = False

        # Moving to Available
        if new_status == "Available":
            deadline_in = json_input.get("deadline", project.responsible_unit.days_in_available)
            new_status_row = self.release_project(
                project=project, current_time=curr_date, deadline_in=deadline_in
            )
        elif new_status == "In Progress":
            new_status_row = self.retract_project(project=project, current_time=curr_date)
        elif new_status == "Expired":
            deadline_in = json_input.get("deadline", project.responsible_unit.days_in_expired)
            new_status_row = self.expire_project(
                project=project, current_time=curr_date, deadline_in=deadline_in
            )
        elif new_status == "Deleted":
            new_status_row, delete_message = self.delete_project(
                project=project, current_time=curr_date
            )
        elif new_status == "Archived":
            is_aborted = json_input.get("is_aborted", False)
            new_status_row, delete_message = self.archive_project(
                project=project, current_time=curr_date, aborted=is_aborted
            )
        else:
            raise DDSArgumentError(message="Invalid status")

        try:
            project.project_statuses.append(new_status_row)
            db.session.commit()
        except (sqlalchemy.exc.OperationalError, sqlalchemy.exc.SQLAlchemyError) as err:
            flask.current_app.logger.exception(err)
            db.session.rollback()
            raise DatabaseError(
                message=str(err),
                alt_message=(
                    "Status was not updated"
                    + (
                        ": Database malfunction."
                        if isinstance(err, sqlalchemy.exc.OperationalError)
                        else ": Server Error."
                    )
                ),
            ) from err

        # Mail users once project is made available
        if new_status == "Available" and send_email:
            for user in project.researchusers:
                AddUser.compose_and_send_email_to_user(
                    userobj=user.researchuser, mail_type="project_release", project=project
                )

        return_message = f"{project.public_id} updated to status {new_status}" + (
            " (aborted)" if new_status == "Archived" and is_aborted else ""
        )

        if new_status != "Available":
            return_message += delete_message + "."
        else:
            return_message += (
                f". An e-mail notification has{' not ' if not send_email else ' '}been sent."
            )
        return {"message": return_message}

    def check_transition_possible(self, current_status, new_status):
        """Check if the transition is valid."""
        valid_statuses = {
            "In Progress": "retract",
            "Available": "release",
            "Deleted": "delete",
            "Expired": "expire",
            "Archived": "archive",
        }
        if new_status not in valid_statuses:
            raise DDSArgumentError("Invalid status")

        possible_transitions = {
            "In Progress": ["Available", "Deleted", "Archived"],
            "Available": ["In Progress", "Expired", "Archived"],
            "Expired": ["Available", "Archived"],
        }

        current_transition = possible_transitions.get(current_status)
        if not current_transition:
            raise DDSArgumentError(
                message=f"Cannot change status for a project that has the status '{current_status}'."
            )

        if new_status not in current_transition:
            raise DDSArgumentError(
                message=(
                    f"You cannot {valid_statuses[new_status]} a "
                    f"project that has the current status '{current_status}'."
                )
            )

    def release_project(
        self, project: models.Project, current_time: datetime.datetime, deadline_in: int
    ) -> models.ProjectStatuses:
        """Release project: Make status Available.

        Only allowed from In Progress and Expired.
        """
        # Check if valid status transition
        self.check_transition_possible(
            current_status=project.current_status, new_status="Available"
        )

        if deadline_in > 90:
            raise DDSArgumentError(
                message="The deadline needs to be less than (or equal to) 90 days."
            )

        deadline = dds_web.utils.current_time(to_midnight=True) + datetime.timedelta(
            days=deadline_in
        )

        # Project can only move from Expired 2 times
        if project.current_status == "Expired":
            if project.times_expired > 2:
                raise DDSArgumentError(
                    "Project availability limit: Project cannot be made Available any more times"
                )
        else:  # current status is in progress
            if project.has_been_available:
                # No change in deadline if made available before
                deadline = project.current_deadline
            else:
                project.released = current_time

        # Create row in ProjectStatuses
        return models.ProjectStatuses(
            status="Available", date_created=current_time, deadline=deadline
        )

    def retract_project(self, project: models.Project, current_time: datetime.datetime):
        """Retract project: Make status In Progress.

        Only possible from Available.
        """
        # Check if valid status transition
        self.check_transition_possible(
            current_status=project.current_status, new_status="In Progress"
        )

        return models.ProjectStatuses(status="In Progress", date_created=current_time)

    def expire_project(
        self, project: models.Project, current_time: datetime.datetime, deadline_in: int
    ) -> models.ProjectStatuses:
        """Expire project: Make status Expired.

        Only possible from Available.
        """
        # Check if valid status transition
        self.check_transition_possible(current_status=project.current_status, new_status="Expired")

        if deadline_in > 30:
            raise DDSArgumentError(
                message="The deadline needs to be less than (or equal to) 30 days."
            )

        deadline = dds_web.utils.current_time(to_midnight=True) + datetime.timedelta(
            days=deadline_in
        )
        return models.ProjectStatuses(
            status="Expired", date_created=current_time, deadline=deadline
        )

    def delete_project(self, project: models.Project, current_time: datetime.datetime):
        """Delete project: Make status Deleted.

        Only possible from In Progress.
        """
        # Check if valid status transition
        self.check_transition_possible(current_status=project.current_status, new_status="Deleted")

        # Can only be Deleted if never made Available
        if project.has_been_available:
            raise DDSArgumentError(
                "You cannot delete a project that has been made available previously. "
                "Please abort the project if you wish to proceed."
            )
        project.is_active = False

        try:
            # Deletes files (also commits session in the function - possibly refactor later)
            RemoveContents().delete_project_contents(project=project)
            self.rm_project_user_keys(project=project)

            # Delete metadata from project row
            self.delete_project_info(proj=project)
        except (TypeError, DatabaseError, DeletionError, BucketNotFoundError) as err:
            flask.current_app.logger.exception(err)
            db.session.rollback()
            raise DeletionError(
                project=project.public_id, message="Server Error: Status was not updated"
            ) from err

        delete_message = (
            f"\nAll files in project '{project.public_id}' deleted and project info cleared"
        )

        return models.ProjectStatuses(status="Deleted", date_created=current_time), delete_message

    def archive_project(
        self, project: models.Project, current_time: datetime.datetime, aborted: bool = False
    ):
        """Archive project: Make status Archived.

        Only possible from In Progress, Available and Expired. Optional aborted flag if something
        has gone wrong.
        """
        # Check if valid status transition
        self.check_transition_possible(current_status=project.current_status, new_status="Archived")
        if project.current_status == "In Progress":
            if project.has_been_available and not aborted:
                raise DDSArgumentError(
                    "You cannot archive a project that has been made available previously. "
                    "Please abort the project if you wish to proceed."
                )
        project.is_active = False

        try:
            # Deletes files (also commits session in the function - possibly refactor later)
            RemoveContents().delete_project_contents(project=project)
            delete_message = f"\nAll files in {project.public_id} deleted"
            self.rm_project_user_keys(project=project)

            # Delete metadata from project row
            if aborted:
                project = self.delete_project_info(project)
                delete_message += " and project info cleared"
        except (TypeError, DatabaseError, DeletionError, BucketNotFoundError) as err:
            flask.current_app.logger.exception(err)
            db.session.rollback()
            raise DeletionError(
                project=project.public_id, message="Server Error: Status was not updated"
            ) from err

        return (
            models.ProjectStatuses(
                status="Archived", date_created=current_time, is_aborted=aborted
            ),
            delete_message,
        )

    def rm_project_user_keys(self, project):
        """Remove ProjectUserKey rows for specified project."""
        for project_key in project.project_user_keys:
            db.session.delete(project_key)

    def delete_project_info(self, proj):
        """Delete certain metadata from proj on deletion/abort"""
        proj.title = None
        proj.date_created = None
        proj.date_updated = None
        proj.description = None
        proj.pi = None
        proj.public_key = None
        # Delete User associations
        for user in proj.researchusers:
            db.session.delete(user)


class GetPublic(flask_restful.Resource):
    """Gets the public key beloning to the current project."""

    @auth.login_required(role=["Unit Admin", "Unit Personnel", "Project Owner", "Researcher"])
    @logging_bind_request
    @handle_validation_errors
    def get(self):
        """Get public key from database."""
        # Verify project ID and access
        project = project_schemas.ProjectRequiredSchema().load(flask.request.args)

        flask.current_app.logger.debug("Getting the public key.")

        if not project.public_key:
            raise KeyNotFoundError(project=project.public_id)

        return {"public": project.public_key.hex().upper()}


class GetPrivate(flask_restful.Resource):
    """Gets the private key belonging to the current project."""

    @auth.login_required(role=["Unit Admin", "Unit Personnel", "Project Owner", "Researcher"])
    @logging_bind_request
    @handle_validation_errors
    def get(self):
        """Get private key from database."""
        # Verify project ID and access
        project = project_schemas.ProjectRequiredSchema().load(flask.request.args)

        flask.current_app.logger.debug("Getting the private key.")

        return flask.jsonify(
            {
                "private": obtain_project_private_key(
                    user=auth.current_user(),
                    project=project,
                    token=dds_web.security.auth.obtain_current_encrypted_token(),
                )
                .hex()
                .upper()
            }
        )


class UserProjects(flask_restful.Resource):
    """Gets all projects registered to a specific user."""

    @auth.login_required
    @logging_bind_request
    def get(self):
        """Get info regarding all projects which user is involved in."""
        return self.format_project_dict(current_user=auth.current_user())

    def format_project_dict(self, current_user):
        """Given a logged in user, fetch projects and return as dict.

        Also used by web/user.py projects_info()
        """
        # TODO: Return different things depending on if unit or not
        all_projects = list()

        # Total number of GB hours and cost saved in the db for the specific unit
        total_bhours_db = 0.0
        total_cost_db = 0.0
        total_size = 0

        usage_arg = flask.request.json.get("usage") if flask.request.json else False
        usage = bool(usage_arg) and current_user.role in [
            "Super Admin",
            "Unit Admin",
            "Unit Personnel",
        ]

        # Get info for all projects
        for p in current_user.projects:
            project_info = {
                "Project ID": p.public_id,
                "Title": p.title,
                "PI": p.pi,
                "Status": p.current_status,
                "Last updated": p.date_updated if p.date_updated else p.date_created,
            }

            # Get proj size and update total size
            proj_size = p.size
            total_size += proj_size
            project_info["Size"] = proj_size

            if usage:
                proj_bhours, proj_cost = self.project_usage(project=p)
                total_bhours_db += proj_bhours
                total_cost_db += proj_cost
                # return ByteHours
                project_info.update({"Usage": proj_bhours, "Cost": proj_cost})

            try:
                project_info["Access"] = (
                    models.ProjectUserKeys.query.filter_by(
                        project_id=p.id, user_id=current_user.username
                    ).count()
                    > 0
                )
            except (sqlalchemy.exc.OperationalError, sqlalchemy.exc.SQLAlchemyError) as err:
                raise DatabaseError(
                    message=str(err),
                    alt_message=(
                        "Could not get users project access information."
                        + (
                            ": Database malfunction."
                            if isinstance(err, sqlalchemy.exc.OperationalError)
                            else "."
                        ),
                    ),
                ) from err

            all_projects.append(project_info)

        return_info = {
            "project_info": all_projects,
            "total_size": total_size,
            "always_show": current_user.role in ["Super Admin", "Unit Admin", "Unit Personnel"],
        }
        if current_user.role in ["Super Admin", "Unit Admin", "Unit Personnel"]:
            return_info["total_usage"] = {
                # return ByteHours
                "usage": total_bhours_db,
                "cost": total_cost_db,
            }

        return return_info

    @staticmethod
    def project_usage(project):

        bhours = 0.0
        cost = 0.0

        for v in project.file_versions:
            # Calculate hours of the current file
            time_deleted = v.time_deleted if v.time_deleted else dds_web.utils.current_time()
            time_uploaded = v.time_uploaded

            file_hours = (time_deleted - time_uploaded).seconds / (60 * 60)

            # Calculate BHours
            bhours += v.size_stored * file_hours

            # Calculate approximate cost per gbhour: kr per gb per month / (days * hours)
            cost_gbhour = 0.09 / (30 * 24)

            # Save file cost to project info and increase total unit cost
            cost += bhours / 1e9 * cost_gbhour

        return bhours, cost


class RemoveContents(flask_restful.Resource):
    """Removes all project contents."""

    @auth.login_required(role=["Unit Admin", "Unit Personnel"])
    @logging_bind_request
    @dbsession
    @handle_validation_errors
    def delete(self):
        """Removes all project contents."""
        # Verify project ID and access
        project = project_schemas.ProjectRequiredSchema().load(flask.request.args)

        # Verify project status ok for deletion
        check_eligibility_for_deletion(
            status=project.current_status, has_been_available=project.has_been_available
        )

        # Check if project contains anything
        if not project.files:
            raise EmptyProjectException(
                project=project, message="There are no project contents to delete."
            )

        # Delete project contents from db and cloud
        self.delete_project_contents(project=project)

        return {"removed": True}

    @staticmethod
    def delete_project_contents(project):
        """Remove project contents"""
        # Delete from cloud
        with ApiS3Connector(project=project) as s3conn:
            try:
                s3conn.remove_bucket()
            except botocore.client.ClientError as err:
                raise DeletionError(message=str(err), project=project.public_id) from err

        # If ok delete from database
        try:
            models.File.query.filter(models.File.project_id == project.id).delete()
            # TODO: put in class
            project.date_updated = dds_web.utils.current_time()

            # Update all versions associated with project
            models.Version.query.filter(
                sqlalchemy.and_(
                    models.Version.project_id == project.id,
                    models.Version.time_deleted.is_(None),
                )
            ).update({"time_deleted": dds_web.utils.current_time()})
        except (
            sqlalchemy.exc.SQLAlchemyError,
            sqlalchemy.exc.OperationalError,
            AttributeError,
        ) as sqlerr:
            raise DeletionError(
                project=project.public_id,
                message=str(sqlerr),
                alt_message=(
                    "Project bucket contents were deleted, but they were not deleted from the "
                    "database. Please contact SciLifeLab Data Centre."
                    + (
                        "Database malfunction."
                        if isinstance(err, sqlalchemy.exc.OperationalError)
                        else "."
                    )
                ),
            ) from sqlerr


class CreateProject(flask_restful.Resource):
    @auth.login_required(role=["Unit Admin", "Unit Personnel"])
    @logging_bind_request
    @json_required
    @handle_validation_errors
    def post(self):
        """Create a new project."""
        p_info = flask.request.json

        # Verify enough number of Unit Admins or return message
        force_create = p_info.pop("force", False)
        if not isinstance(force_create, bool):
            raise DDSArgumentError(message="`force` is a boolean value: True or False.")

        warning_message = dds_web.utils.verify_enough_unit_admins(
            unit_id=auth.current_user().unit.id, force_create=force_create
        )
        if warning_message:
            return {"warning": warning_message}

        # Add a new project to db
        try:
            new_project = project_schemas.CreateProjectSchema().load(p_info)
            db.session.add(new_project)
        except sqlalchemy.exc.OperationalError as err:
            raise DatabaseError(message=str(err), alt_message="Unexpected database error.")

        if not new_project:
            raise DDSArgumentError("Failed to create project.")

        # TODO: Change -- the bucket should be created before the row is added to the database
        # This is a quick fix so that things do not break
        with ApiS3Connector(project=new_project) as s3:
            try:
                s3.resource.create_bucket(Bucket=new_project.bucket)
            except (
                botocore.exceptions.ClientError,
                botocore.exceptions.ParamValidationError,
            ) as err:
                # For now just keeping the project row
                raise S3ConnectionError(str(err)) from err

        try:
            db.session.commit()
        except (sqlalchemy.exc.SQLAlchemyError, sqlalchemy.exc.OperationalError, TypeError) as err:
            flask.current_app.logger.exception(err)
            db.session.rollback()
            raise DatabaseError(
                message=str(err),
                alt_message=(
                    "Project was not created"
                    + (
                        ": Database malfunction."
                        if isinstance(err, sqlalchemy.exc.OperationalError)
                        else ": Server error."
                    ),
                ),
            ) from err
        except (
            marshmallow.exceptions.ValidationError,
            DDSArgumentError,
            AccessDeniedError,
        ) as err:
            flask.current_app.logger.exception(err)
            db.session.rollback()
            raise

        flask.current_app.logger.debug(
            f"Project {new_project.public_id} created by user {auth.current_user().username}."
        )

        user_addition_statuses = []
        if "users_to_add" in p_info:
            for user in p_info["users_to_add"]:
                try:
                    existing_user = user_schemas.UserSchema().load(user)
                    unanswered_invite = user_schemas.UnansweredInvite().load(user)
                except (
                    marshmallow.exceptions.ValidationError,
                    sqlalchemy.exc.OperationalError,
                ) as err:
                    if isinstance(err, sqlalchemy.exc.OperationalError):
                        flask.current_app.logger.error(err)
                        addition_status = "Unexpected database error."
                    else:
                        addition_status = f"Error for '{user.get('email')}': {err}"
                    user_addition_statuses.append(addition_status)
                    continue

                if not existing_user and not unanswered_invite:
                    # Send invite if the user doesn't exist
                    invite_user_result = AddUser.invite_user(
                        email=user.get("email"),
                        new_user_role=user.get("role"),
                        project=new_project,
                    )

                    if invite_user_result["status"] == http.HTTPStatus.OK:
                        invite_msg = (
                            f"Invitation sent to {user['email']}. "
                            "The user should have a valid account to be added to a project"
                        )
                    else:
                        invite_msg = invite_user_result["message"]
                    user_addition_statuses.append(invite_msg)
                else:
                    # If it is an existing user, add them to project.
                    addition_status = ""
                    try:
                        add_user_result = AddUser.add_to_project(
                            whom=existing_user or unanswered_invite,
                            project=new_project,
                            role=user.get("role"),
                        )
                    except DatabaseError as err:
                        addition_status = f"Error for '{user['email']}': {err.description}"
                    else:
                        addition_status = add_user_result["message"]
                    user_addition_statuses.append(addition_status)

        return {
            "status": http.HTTPStatus.OK,
            "message": f"Added new project '{new_project.title}'",
            "project_id": new_project.public_id,
            "user_addition_statuses": user_addition_statuses,
        }


class ProjectUsers(flask_restful.Resource):
    """Get all users in a specific project."""

    @auth.login_required
    @logging_bind_request
    @handle_validation_errors
    def get(self):
        # Verify project ID and access
        project = project_schemas.ProjectRequiredSchema().load(flask.request.args)

        # Get info on research users
        research_users = list()

        for user in project.researchusers:
            user_info = {
                "User Name": user.user_id,
                "Primary email": "",
                "Role": "Owner" if user.owner else "Researcher",
            }
            for user_email in user.researchuser.emails:
                if user_email.primary:
                    user_info["Primary email"] = user_email.email
            research_users.append(user_info)

        for invitee in project.project_invite_keys:
            role = "Owner" if invitee.owner else "Researcher"
            user_info = {
                "User Name": "NA (Pending)",
                "Primary email": f"{invitee.invite.email} (Pending)",
                "Role": f"{role} (Pending)",
            }
            research_users.append(user_info)

        return {"research_users": research_users}


class ProjectAccess(flask_restful.Resource):
    """Renew project access for users."""

    @auth.login_required(role=["Unit Admin", "Unit Personnel", "Project Owner"])
    @logging_bind_request
    @dbsession
    @json_required
    @handle_validation_errors
    def post(self):
        """Give access to user."""
        # Verify that user specified
        json_input = flask.request.json

        if "email" not in json_input:
            raise DDSArgumentError(message="User email missing.")

        user = user_schemas.UserSchema().load({"email": json_input.pop("email")})

        if not user:
            raise NoSuchUserError()

        # Verify that project specified
        project_info = flask.request.args
        project = None
        if project_info and project_info.get("project"):
            project = project_schemas.ProjectRequiredSchema().load(project_info)

        # Verify permission to give user access
        self.verify_renew_access_permission(user=user, project=project)

        # Give access to specific project or all active projects if no project specified
        list_of_projects = None
        if not project:
            if user.role == "Researcher":
                list_of_projects = [x.project for x in user.project_associations]
            elif user.role in ["Unit Personnel", "Unit Admin"]:
                list_of_projects = user.unit.projects
        else:
            list_of_projects = [project]

        errors = self.give_project_access(
            project_list=list_of_projects, current_user=auth.current_user(), user=user
        )
        if errors:
            return {"errors": errors}

        return {"message": f"Project access updated for user '{user.primary_email}'."}

    @staticmethod
    def verify_renew_access_permission(user, project):
        """Check that user has permission to give access to another user in this project."""

        if auth.current_user() == user:
            raise AccessDeniedError(message="You cannot renew your own access.")

        # Get roles
        current_user_role = get_user_roles_common(user=auth.current_user())
        other_user_role = get_user_roles_common(user=user)

        # Check access
        if not (
            (
                current_user_role == "Unit Admin"
                and other_user_role
                in ["Unit Admin", "Unit Personnel", "Project Owner", "Researcher"]
            )
            or (
                current_user_role == "Unit Personnel"
                and other_user_role in ["Unit Personnel", "Project Owner", "Researcher"]
            )
            or (
                current_user_role == "Project Owner"
                and other_user_role in ["Project Owner", "Researcher"]
            )
        ):
            raise AccessDeniedError(
                message=(
                    "You do not have the necessary permissions "
                    "to shared project access with this user."
                )
            )

    @staticmethod
    def give_project_access(project_list, current_user, user):
        """Give specific user project access."""
        # Loop through and check that the project(s) is(are) active
        fix_errors = {}
        for proj in project_list:
            try:
                if proj.is_active:
                    project_keys_row = models.ProjectUserKeys.query.filter_by(
                        project_id=proj.id, user_id=user.username
                    ).one_or_none()
                    if not project_keys_row:
                        share_project_private_key(
                            from_user=current_user,
                            to_another=user,
                            project=proj,
                            from_user_token=dds_web.security.auth.obtain_current_encrypted_token(),
                        )
            except KeyNotFoundError as keyerr:
                fix_errors[
                    proj.public_id
                ] = "You do not have access to this project. Please contact the responsible unit."

        return fix_errors
