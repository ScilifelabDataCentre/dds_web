from werkzeug.exceptions import HTTPException


class BucketNameNotFoundError(HTTPException):
    pass


class ProjectSizeError(HTTPException):
    pass


class DBFileError(HTTPException):
    pass


class FolderSizeError(HTTPException):
    pass


class FileDeletionError(HTTPException):
    pass


class ItemDeletionError(HTTPException):
    pass


class FileRetrievalError(HTTPException):
    pass


errors = {
    "BucketNameNotFoundError": {"message": "Could not get S3 bucket name.", "status": 500},
    "ProjectSizeError": {"message": "Could not get size of project.", "status": 500},
    "DBFileError": {"message": "Failed to get files from database.", "status": 500},
    "FolderSizeError": {"message": "Failed to calculate folder size.", "status": 500},
    "FileDeletionError": {"message": "Deletion of file(s) from database failed.", "status": 500},
    "ItemDeletionError": {"message": "Removal of item(s) from S3 bucket failed.", "status": 500},
    "FileRetrievalError": {"message": "Retrieval of file(s) from database failed.", "status": 500},
}
