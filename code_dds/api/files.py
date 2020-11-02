"""File-related API endpoints.

Handles listing and updating of the 'Files'-table.
"""

###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library

# Installed
import sqlalchemy
import flask
import flask_restful

# Own modules
from code_dds import db
from code_dds import models
from code_dds import marshmallows as marmal
from code_dds import timestamp
from code_dds.api import login
from code_dds.api import project  # import update_project_size


###############################################################################
# ENDPOINTS ####################################################### ENDPOINTS #
###############################################################################

class ListFiles(flask_restful.Resource):
    """Lists all files in db."""

    def get(self):
        """"Gets files from db and returns them in request response."""

        all_files = models.File.query.all()
        return marmal.files_schema.dump(all_files)


class FileSalt(flask_restful.Resource):
    """Gets the salt used to derive decryption key."""

    def get(self, file_id):
        """Gets salt from db and returns response in json."""

        file_salt = models.File.query.filter_by(id=file_id)

        if file_salt is None:
            return flask.jsonify(found=False, salt="")

        return flask.jsonify(found=True, salt=file_salt.salt)


class DeliveryDate(flask_restful.Resource):
    """Updates the delivery dates."""

    def post(self):
        """Update latest download date in file database.

        Returns:
            json:   If updated
        """

        # Validate token and cancel delivery if not valid
        token = flask.request.args["token"]
        proj = flask.request.args["project"]
        ok_ = login.validate_token(token, proj)
        if not ok_:
            return flask.jsonify(access_granted=False,
                                 updated=False,
                                 message="Token expired. Access denied.")

        # Get file id
        file_id = flask.request.args["file_id"]

        # Update file info
        try:
            file = models.File.query.filter_by(id=int(file_id)).first()
        except sqlalchemy.exc.SQLAlchemyError as e:
            print(str(e), flush=True)
            return flask.jsonify(access_granted=True, updated=False,
                                 message=str(e))

        if file is None:
            emess = "The file does not exist in the database, cannot update."
            print(emess, flush=True)
            return flask.jsonify(access_granted=True, updated=False,
                                 message=emess)

        # Update download time
        try:
            file.latest_download = timestamp()
        except sqlalchemy.exc.SQLAlchemyError as e:
            print(str(e), flush=True)
            return flask.jsonify(access_granted=True, updated=False,
                                 message=str(e))
        else:
            db.session.commit()

        return flask.jsonify(access_granted=True, updated=True, message="")


class FileUpdate(flask_restful.Resource):
    """Creates or updates the file information."""

    def post(self):
        """Add to or update file in database.

        Returns:
            json: access (bool), updated (bool), message (str)
        """

        # Get all params from request
        all_ = flask.request.args

        # Validate token and cancel delivery if not valid
        ok_ = login.validate_token(all_["token"], all_["project"])
        if not ok_:
            return flask.jsonify(access_granted=False,
                                 updated=False,
                                 message="Token expired. Access denied.")

        # Add file info to db
        try:
            # Get existing file
            existing_file = models.File.query.filter_by(
                name=all_["file"], project_id=all_["project"]
            ).first()
        except sqlalchemy.exc.SQLAlchemyError as e:
            print("\nError occurred! {e}\n", flush=True)
            return flask.jsonify(access_granted=True, updated=False,
                                 message=str(e))
        else:
            size = int(all_["size"])            # File size
            size_enc = int(all_["size_enc"])    # Encrypted file size

            # Add new file if it doesn't already exist in db
            if existing_file is None:
                try:
                    new_file = models.File(
                        name=all_["file"],
                        directory_path=all_["directory_path"],
                        size=size,
                        size_enc=size_enc,
                        extension=all_["extension"],
                        compressed=bool(all_["ds_compressed"] == "True"),
                        public_key=all_["key"],
                        salt=all_["salt"],
                        project_id=all_["project"]
                    )
                except sqlalchemy.exc.SQLAlchemyError as e:
                    return flask.jsonify(access_granted=True, updated=False,
                                         message=str(e))
                else:
                    # Add new info to db
                    db.session.add(new_file)

                    # Update project size
                    proj_updated, error = project.update_project_size(
                        proj_id=all_["project"],
                        altered_size=size,
                        altered_enc_size=size_enc,
                        method="insert"
                    )

                    # If project size updated, commit to session to save to db
                    if proj_updated:
                        try:
                            db.session.commit()
                        except sqlalchemy.exc.SQLAlchemyError as e:
                            return flask.jsonify(access_granted=True,
                                                 updated=False,
                                                 message=str(e))
                        else:
                            return flask.jsonify(access_granted=True,
                                                 updated=True,
                                                 message="")
                    else:
                        return flask.jsonify(access_granted=True,
                                             updated=False,
                                             message=error)
            else:
                if all_["overwrite"]:
                    old_size = existing_file.size   # Curr file size in db
                    old_enc_size = existing_file.size_enc   # Curr enc size db

                    # Update file if it exists in db
                    try:
                        existing_file.name = all_["file"]
                        existing_file.directory_path = all_["directory_path"]
                        existing_file.size = size
                        existing_file.size_enc = size_enc
                        existing_file.extension = all_["extension"]
                        existing_file.compressed = bool(all_["ds_compressed"])
                        existing_file.date_uploaded = timestamp()
                        existing_file.public_key = all_["key"]
                        existing_file.salt = all_["salt"]
                        existing_file.project_id = int(all_["project"])
                    except sqlalchemy.exc.SQLAlchemyError as e:
                        return flask.jsonify(access_granted=True,
                                             updated=False,
                                             message=str(e))
                    else:
                        # Update project size
                        proj_updated, error = project.update_project_size(
                            proj_id=all_["project"],
                            altered_size=size,
                            altered_enc_size=size_enc,
                            method="update",
                            old_size=old_size,
                            old_enc_size=old_enc_size
                        )

                        # If project size updated, commit to session to save
                        if proj_updated:
                            try:
                                db.session.commit()
                            except sqlalchemy.exc.SQLAlchemyError as e:
                                return flask.jsonify(access_granted=True,
                                                     updated=False,
                                                     message=str(e))
                            else:
                                return flask.jsonify(access_granted=True,
                                                     updated=True, message="")
                        else:
                            return flask.jsonify(access_granted=True,
                                                 updated=False,
                                                 message=error)
                else:
                    return flask.jsonify(
                        access_granted=True, updated=False,
                        message=("Trying to overwrite delivered "
                                 "file but 'overwrite' option not "
                                 "specified.")
                    )

        return flask.jsonify(access_granted=True, updated=True, message="")
