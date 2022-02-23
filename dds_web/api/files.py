"""Files module."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library
import os

# Installed
import flask_restful
import flask
import sqlalchemy
import werkzeug
import botocore

# Own modules
import dds_web.utils
from dds_web import auth
from dds_web.database import models
from dds_web import db
from dds_web.api.api_s3_connector import ApiS3Connector
from dds_web.api.dds_decorators import (
    logging_bind_request,
    json_required,
    handle_validation_errors,
)
from dds_web.errors import (
    AccessDeniedError,
    DatabaseError,
    DDSArgumentError,
    EmptyProjectException,
    NoSuchFileError,
    S3ConnectionError,
)
from dds_web.api.schemas import file_schemas
from dds_web.api.schemas import project_schemas


def check_eligibility_for_upload(status):
    """Check if a project status is eligible for upload/modification"""
    if status != "In Progress":
        raise DDSArgumentError("Project not in right status to upload/modify files.")
    return True


def check_eligibility_for_download(status, user_role):
    """Check if a project status makes it eligible to download"""
    if status == "Available" or (
        status == "In Progress" and user_role in ["Unit Admin", "Unit Personnel"]
    ):
        return True

    raise DDSArgumentError("Current Project status limits file download.")


def check_eligibility_for_deletion(status, has_been_available):
    """Check if a project status is eligible for deletion"""
    if status not in ["In Progress"]:
        raise DDSArgumentError("Project Status prevents files from being deleted.")

    if has_been_available:
        raise DDSArgumentError(
            "Existing project contents cannot be deleted since the project has been previously made available to recipients."
        )
    return True


####################################################################################################
# ENDPOINTS ############################################################################ ENDPOINTS #
####################################################################################################


class NewFile(flask_restful.Resource):
    """Inserts a file into the database"""

    @auth.login_required(role=["Super Admin", "Unit Admin", "Unit Personnel"])
    @logging_bind_request
    @json_required
    @handle_validation_errors
    def post(self):
        """Add new file to DB."""
        # Verify project id and access
        project = project_schemas.ProjectRequiredSchema().load(flask.request.args)

        # Verify that project has correct status for upload
        check_eligibility_for_upload(status=project.current_status)

        # Create new files
        new_file = file_schemas.NewFileSchema().load(
            {**flask.request.json, "project": project.public_id}
        )

        try:
            db.session.commit()
        except sqlalchemy.exc.SQLAlchemyError as err:
            flask.current_app.logger.debug(err)
            db.session.rollback()
            raise DatabaseError(f"Failed to add new file to database.")

        return {"message": f"File '{new_file.name}' added to db."}

    @auth.login_required(role=["Super Admin", "Unit Admin", "Unit Personnel"])
    @logging_bind_request
    @handle_validation_errors
    def put(self):
        """Update existing file."""
        # Verify project ID and access
        project = project_schemas.ProjectRequiredSchema().load(flask.request.args)

        # Verify that projet has correct status for upload
        check_eligibility_for_upload(status=project.current_status)

        file_info = flask.request.json
        if not all(x in file_info for x in ["name", "name_in_bucket", "subpath", "size"]):
            raise DDSArgumentError("Information is missing, cannot add file to database.")

        try:
            # Check if file already in db
            existing_file = models.File.query.filter(
                sqlalchemy.and_(
                    models.File.name == sqlalchemy.func.binary(file_info.get("name")),
                    models.File.project_id == project.id,
                )
            ).first()

            # Error if not found
            if not existing_file or existing_file is None:
                raise NoSuchFileError(
                    "Cannot update non-existent file "
                    f"'{werkzeug.utils.secure_filename(file_info.get('name'))}' in the database!"
                )

            # Get version row
            current_file_version = models.Version.query.filter(
                sqlalchemy.and_(
                    models.Version.active_file == sqlalchemy.func.binary(existing_file.id),
                    models.Version.time_deleted.is_(None),
                )
            ).all()
            if len(current_file_version) > 1:
                flask.current_app.logger.warning(
                    "There is more than one version of the file "
                    "which does not yet have a deletion timestamp."
                )

            # Same timestamp for deleted and created new file
            new_timestamp = dds_web.utils.current_time()

            # Overwritten == deleted/deactivated
            for version in current_file_version:
                if version.time_deleted is None:
                    version.time_deleted = new_timestamp

            # Update file info
            existing_file.subpath = file_info.get("subpath")
            existing_file.size_original = file_info.get("size")
            existing_file.size_stored = file_info.get("size_processed")
            existing_file.compressed = file_info.get("compressed")
            existing_file.salt = file_info.get("salt")
            existing_file.public_key = file_info.get("public_key")
            existing_file.time_uploaded = new_timestamp
            existing_file.checksum = file_info.get("checksum")

            # New version
            new_version = models.Version(
                size_stored=file_info.get("size_processed"),
                time_uploaded=new_timestamp,
                active_file=existing_file.id,
                project_id=project,
            )

            # Update foreign keys and relationships
            project.file_versions.append(new_version)
            existing_file.versions.append(new_version)

            db.session.add(new_version)
            db.session.commit()
        except sqlalchemy.exc.SQLAlchemyError as err:
            db.session.rollback()
            raise DatabaseError(f"Failed updating file information: {err}")

        return {"message": f"File '{file_info.get('name')}' updated in db."}


class MatchFiles(flask_restful.Resource):
    """Checks for matching files in database"""

    @auth.login_required(role=["Super Admin", "Unit Admin", "Unit Personnel"])
    @logging_bind_request
    @json_required
    @handle_validation_errors
    def get(self):
        """Get name in bucket for all files specified."""
        # Verify project ID and access
        project = project_schemas.ProjectRequiredSchema().load(flask.request.args)

        # Verify project has correct status for upload
        check_eligibility_for_upload(status=project.current_status)

        # Get files specified
        try:
            matching_files = (
                models.File.query.filter(models.File.name.in_(flask.request.json))
                .filter(models.File.project_id == sqlalchemy.func.binary(project.id))
                .all()
            )
        except sqlalchemy.exc.SQLAlchemyError as err:
            raise DatabaseError(f"Failed to get matching files in db: {err}")

        # The files checked are not in the db
        if not matching_files or matching_files is None:
            return {"files": None}

        return {"files": {x.name: x.name_in_bucket for x in matching_files}}


class ListFiles(flask_restful.Resource):
    """Lists files within a project"""

    @auth.login_required
    @logging_bind_request
    @handle_validation_errors
    def get(self):
        """Get a list of files within the specified folder."""
        # Verify project ID and access
        project = project_schemas.ProjectRequiredSchema().load(flask.request.args)

        if auth.current_user().role == "Researcher" and project.current_status == "In Progress":
            raise AccessDeniedError(message="There's no data available at this time.")

        extra_args = flask.request.json
        if extra_args is None:
            extra_args = {}

        # Check if to return file size
        show_size = extra_args.get("show_size")

        # Check if to get from root or folder
        subpath = "."
        if extra_args.get("subpath"):
            subpath = extra_args.get("subpath").rstrip(os.sep)

        files_folders = list()

        # Check project not empty
        if project.num_files == 0:
            return {"num_items": 0, "message": f"The project {project.public_id} is empty."}

        # Get files and folders
        try:
            distinct_files, distinct_folders = self.items_in_subpath(
                project=project, folder=subpath
            )
        except DatabaseError:
            raise

        # Collect file and folder info to return to CLI
        if distinct_files:
            for x in distinct_files:
                info = {
                    "name": x[0] if subpath == "." else x[0].split(os.sep)[-1],
                    "folder": False,
                }
                if show_size:
                    info.update({"size": dds_web.utils.format_byte_size(x[1])})
                files_folders.append(info)
        if distinct_folders:
            for x in distinct_folders:
                info = {
                    "name": x if subpath == "." else x.split(os.sep)[-1],
                    "folder": True,
                }

                if show_size:
                    folder_size = self.get_folder_size(project=project, folder_name=x)
                    info.update({"size": dds_web.utils.format_byte_size(folder_size)})
                files_folders.append(info)

        return {"files_folders": files_folders}

    def get_folder_size(self, project, folder_name):
        """Get total size of folder."""
        # Sum up folder file sizes
        try:
            file_info = (
                models.File.query.with_entities(
                    sqlalchemy.func.sum(models.File.size_original).label("sizeSum")
                )
                .filter(
                    sqlalchemy.and_(
                        models.File.project_id == sqlalchemy.func.binary(project.id),
                        models.File.subpath.like(f"{folder_name}%"),
                    )
                )
                .first()
            )

        except sqlalchemy.exc.SQLAlchemyError as err:
            raise DatabaseError(message=str(err))

        return file_info.sizeSum

    @staticmethod
    def items_in_subpath(project, folder="."):
        """Get all items in root folder of project."""
        distinct_files = []
        distinct_folders = []
        # Get everything in root:
        # Files have subpath "." and folders do not have child folders
        # Get everything in folder:
        # Files have subpath == folder and folders have child folders (regexp)
        try:
            # All files in project
            files = models.File.query.filter(
                models.File.project_id == sqlalchemy.func.binary(project.id)
            )

            # File names in root
            distinct_files = (
                files.filter(models.File.subpath == sqlalchemy.func.binary(folder))
                .with_entities(models.File.name, models.File.size_original)
                .all()
            )

            # Folder names in folder (or root)
            if folder == ".":
                # Get distinct folders in root, subpath should not be "."
                distinct_folders = (
                    files.filter(models.File.subpath != sqlalchemy.func.binary(folder))
                    .with_entities(models.File.subpath)
                    .distinct()
                    .all()
                )

                # Get first subpath (may be many and first may not have files in)
                first_parts = set(x[0].split(os.sep)[0] for x in distinct_folders)
                distinct_folders = list(first_parts)

            else:
                # Get distinct sub folders in specific folder with regex
                # Match /<something that is not /> x number of times
                distinct_folders = (
                    files.filter(models.File.subpath.regexp_match(rf"^{folder}(/[^/]+)+$"))
                    .with_entities(models.File.subpath)
                    .distinct()
                    .all()
                )

                # Get length of specified folder
                len_folder = len(folder.split(os.sep))

                # Get subfolders in level under specified folder
                split_paths = set(
                    f"{os.sep}".join(x[0].split(os.sep)[: len_folder + 1]) for x in distinct_folders
                )
                distinct_folders = list(split_paths)

        except sqlalchemy.exc.SQLAlchemyError as err:
            raise DatabaseError(message=str(err))
        else:
            return distinct_files, distinct_folders


class RemoveFile(flask_restful.Resource):
    """Removes files from the database and s3 with boto3."""

    @auth.login_required(role=["Super Admin", "Unit Admin", "Unit Personnel"])
    @logging_bind_request
    @json_required
    @handle_validation_errors
    def delete(self):
        """Delete file(s)."""
        # Verify project ID and access
        project = project_schemas.ProjectRequiredSchema().load(flask.request.args)

        # Verify project status ok for deletion
        check_eligibility_for_deletion(
            status=project.current_status, has_been_available=project.has_been_available
        )

        # Delete file(s) from db and cloud
        not_removed_dict, not_exist_list = self.delete_multiple(
            project=project, files=flask.request.json
        )

        # Return deleted and not deleted files
        return {"not_removed": not_removed_dict, "not_exists": not_exist_list}

    def delete_multiple(self, project, files):
        """Delete multiple files."""

        not_removed_dict, not_exist_list = ({}, [])

        with ApiS3Connector(project=project) as s3conn:

            # Delete each file
            for x in files:
                # Delete from db
                try:
                    name_in_bucket = self.delete_one(project=project, filename=x)
                    if not name_in_bucket:
                        raise DatabaseError(
                            message="Remote file name not found.", pass_message=True
                        )
                except FileNotFoundError:
                    db.session.rollback()
                    not_exist_list.append(x)
                    continue
                except (sqlalchemy.exc.SQLAlchemyError, DatabaseError) as err:
                    db.session.rollback()
                    not_removed_dict[x] = str(err)
                    continue

                # Remove from s3 bucket
                try:
                    s3conn.remove_one(file=name_in_bucket)
                except (BucketNotFoundError, botocore.client.ClientError) as err:
                    db.session.rollback()
                    not_removed_dict[x] = str(err)
                    continue

                # Commit to db if ok
                try:
                    db.session.commit()
                except sqlalchemy.exc.SQLAlchemyError as err:
                    db.session.rollback()
                    not_removed_dict[x] = str(err)
                    continue

        return not_removed_dict, not_exist_list

    def delete_one(self, project, filename):
        """Delete a single file in project."""
        # Get matching files in project
        file = models.File.query.filter(
            models.File.name == sqlalchemy.func.binary(filename),
            models.File.project_id == sqlalchemy.func.binary(project.id),
        ).one_or_none()

        if not file:
            raise FileNotFoundError("Could not find the specified file.")

        name_in_bucket = file.name_in_bucket

        # get current version
        current_file_version = models.Version.query.filter(
            sqlalchemy.and_(
                models.Version.active_file == sqlalchemy.func.binary(file.id),
                models.Version.time_deleted.is_(None),
            )
        ).first()
        current_file_version.time_deleted = dds_web.utils.current_time()

        db.session.delete(file)
        project.date_updated = dds_web.utils.current_time()

        return name_in_bucket


class RemoveDir(flask_restful.Resource):
    """Removes one or more full directories from the database and s3."""

    @auth.login_required(role=["Super Admin", "Unit Admin", "Unit Personnel"])
    @logging_bind_request
    @json_required
    @handle_validation_errors
    def delete(self):
        """Delete folder(s)."""
        # Verify project ID and access
        project = project_schemas.ProjectRequiredSchema().load(flask.request.args)

        # Verify project status ok for deletion
        check_eligibility_for_deletion(
            status=project.current_status, has_been_available=project.has_been_available
        )

        # Remove folder(s)
        not_removed_dict, not_exist_list = ({}, [])
        try:

            with ApiS3Connector(project=project) as s3conn:

                for x in flask.request.json:
                    # Get all files in the folder
                    try:
                        in_db, objects_to_delete = self.delete_folder(project=project, folder=x)
                        if not in_db:
                            not_exist_list.append(x)
                            raise FileNotFoundError(
                                "Could not find the specified folder in the database."
                            )
                    except (sqlalchemy.exc.SQLAlchemyError, FileNotFoundError) as err:
                        db.session.rollback()
                        not_removed_dict[x] = str(err)
                        continue

                    # Delete from s3
                    try:
                        s3conn.remove_multiple(items=objects_to_delete)
                    except botocore.client.ClientError as err:
                        db.session.rollback()
                        not_removed_dict[x] = str(err)
                        continue

                    # Commit to db if no error so far
                    try:
                        db.session.commit()
                    except sqlalchemy.exc.SQLAlchemyError as err:
                        db.session.rollback()
                        not_removed_dict[x] = str(err)
                        continue
        except (ValueError,):
            raise
        return {"not_removed": not_removed_dict, "not_exists": not_exist_list}

    def delete_folder(self, project, folder):
        """Delete all items in folder"""
        exists = False
        names_in_bucket = []
        try:
            # File names in root
            files = (
                models.File.query.filter(
                    models.File.project_id == sqlalchemy.func.binary(project.id)
                )
                .filter(
                    sqlalchemy.or_(
                        models.File.subpath == sqlalchemy.func.binary(folder),
                        models.File.subpath.regexp_match(rf"^{folder}(/[^/]+)*$"),
                    )
                )
                .all()
            )
        except sqlalchemy.exc.SQLAlchemyError as err:
            raise DatabaseError(message=str(err))

        if files:
            exists = True
            for x in files:
                # get current version
                current_file_version = models.Version.query.filter(
                    sqlalchemy.and_(
                        models.Version.active_file == sqlalchemy.func.binary(x.id),
                        models.Version.time_deleted.is_(None),
                    )
                ).first()
                current_file_version.time_deleted = dds_web.utils.current_time()

                # Delete file and update project size
                names_in_bucket.append(x.name_in_bucket)
                db.session.delete(x)
            project.date_updated = dds_web.utils.current_time()

        return exists, names_in_bucket


class FileInfo(flask_restful.Resource):
    """Get file info on files to download."""

    @auth.login_required
    @logging_bind_request
    @json_required
    @handle_validation_errors
    def get(self):
        """Checks which files can be downloaded, and get their info."""
        # Verify project ID and access
        project = project_schemas.ProjectRequiredSchema().load(flask.request.args)

        # Verify project status ok for download
        user_role = auth.current_user().role
        check_eligibility_for_download(status=project.current_status, user_role=user_role)

        # Get project contents
        input_ = {
            "project": project.public_id,
            **{"requested_items": flask.request.json, "url": True},
        }
        (
            found_files,
            found_folder_contents,
            not_found,
        ) = project_schemas.ProjectContentSchema().dump(input_)

        return {
            "files": found_files,
            "folder_contents": found_folder_contents,
            "not_found": not_found,
        }


class FileInfoAll(flask_restful.Resource):
    """Get info on all project files."""

    @auth.login_required
    @logging_bind_request
    @handle_validation_errors
    def get(self):
        """Get file info on all files."""
        # Verify project ID and access
        project = project_schemas.ProjectRequiredSchema().load(flask.request.args)

        # Verify project status ok for download
        user_role = auth.current_user().role
        check_eligibility_for_download(status=project.current_status, user_role=user_role)

        files, _, _ = project_schemas.ProjectContentSchema().dump(
            {"project": project.public_id, "get_all": True, "url": True}
        )

        return {"files": files}


class UpdateFile(flask_restful.Resource):
    """Update file info after download"""

    @auth.login_required
    @logging_bind_request
    @json_required
    @handle_validation_errors
    def put(self):
        """Update info in db."""
        # Verify project ID and access
        project = project_schemas.ProjectRequiredSchema().load(flask.request.args)

        # Get file name from request from CLI
        file_name = flask.request.json.get("name")
        if not file_name:
            raise DDSArgumentError("No file name specified. Cannot update file.")

        # Update file info
        try:
            flask.current_app.logger.debug(
                "Updating file in current project: %s", project.public_id
            )

            flask.current_app.logger.debug(f"File name: {file_name}")
            file = models.File.query.filter(
                sqlalchemy.and_(
                    models.File.project_id == sqlalchemy.func.binary(project.id),
                    models.File.name == sqlalchemy.func.binary(file_name),
                )
            ).first()

            if not file:
                raise NoSuchFileError()

            file.time_latest_download = dds_web.utils.current_time()
        except sqlalchemy.exc.SQLAlchemyError as err:
            db.session.rollback()
            flask.current_app.logger.exception(str(err))
            raise DatabaseError("Update of file info failed.")
        else:
            # flask.current_app.logger.debug("File %s updated", file_name)
            db.session.commit()

        return {"message": "File info updated."}
