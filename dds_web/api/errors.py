from werkzeug import exceptions


class MissingCredentialsError(exceptions.HTTPException):
    pass


class ItemDeletionError(exceptions.HTTPException):
    pass


class DatabaseError(exceptions.HTTPException):
    """ """


errors = {
    "ItemDeletionError": {"message": "Removal of item(s) from S3 bucket failed.", "status": 500},
    "MissingCredentialsError": {"message": "Missing username and/or password.", "status": 400},
    "DatabaseError": {
        "message": "DDS Database encountered a Flask-SQLAlchemy error.",
        "status": 500,
    },
}
