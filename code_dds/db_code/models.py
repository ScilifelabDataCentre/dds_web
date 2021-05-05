"""Data models."""

# IMPORTS ########################################################### IMPORTS #

# Standard library
# import datetime
# import pytz

# Installed
# from sqlalchemy import func, DDL, event

# Own modules
from code_dds import db

# CLASSES ########################################################### CLASSES #


# class Tokens(db.Model):
#     """Data model for access tokens."""

#     # Table setup
#     __tablename__ = 'tokens'
#     __table_args__ = {'extend_existing': True}

#     # Columns
#     id = db.Column(db.Integer, primary_key=True, autoincrement=True)
#     token = db.Column(db.String(50), unique=True, nullable=False)
#     created = db.Column(db.String(50), unique=False, nullable=False)
#     expires = db.Column(db.String(50), unique=False, nullable=False)
#     project_id = db.Column(db.String(32), db.ForeignKey('projects.id'),
#                            unique=False, nullable=False)


class User(db.Model):
    """Data model for user accounts."""

    # Table setup
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    # Columns
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    public_id = db.Column(db.String(50), unique=True, nullable=False)
    # first_name = db.Column(db.String(50), unique=False, nullable=False)
    # last_name = db.Column(db.String(50), unique=False, nullable=False)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(120), unique=False, nullable=False)
    # settings = db.Column(db.String(50), unique=False, nullable=False)
    # email = db.Column(db.String(80), unique=True, nullable=False)
    # phone = db.Column(db.String(20), unique=False, nullable=True)
    admin = db.Column(db.Boolean, unique=False, nullable=False)

    # Relationships
    user_projects = db.relationship(
        "Project", backref="project_user", lazy=True, foreign_keys="Project.owner"
    )

    def __repr__(self):
        """Called by print, creates representation of object"""

        return f"<User {self.username}>"


class Facility(db.Model):
    """Data model for facility accounts."""

    # Table setup
    __tablename__ = "facilities"
    __table_args__ = {"extend_existing": True}

    # Columns
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    public_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), unique=True, nullable=False)
    internal_ref = db.Column(db.String(10), unique=True, nullable=False)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(120), unique=False, nullable=False)
    # settings = db.Column(db.String(50), unique=False, nullable=False)
    # email = db.Column(db.String(80), unique=True, nullable=False)
    # phone = db.Column(db.String(20), unique=False, nullable=True)
    safespring = db.Column(db.String(120), unique=False, nullable=False)  # unique=True later

    # Relationships
    user_projects = db.relationship(
        "Project",
        backref="project_facility",
        lazy=True,
        foreign_keys="Project.facility",
    )

    def __repr__(self):
        """Called by print, creates representation of object"""

        return f"<Facility {self.username}>"


class Role(db.Model):
    """Data model for roles - used to find correct table."""

    # Table setup
    __tablename__ = "roles"
    __table_args__ = {"extend_existing": True}

    # Columns
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    facility = db.Column(db.Boolean, unique=False, nullable=False)


class Project(db.Model):
    """Data model for projects."""

    # Table setup
    __tablename__ = "projects"
    __table_args__ = {"extend_existing": True}

    # Columns
    id = db.Column(db.String(32), primary_key=True)
    title = db.Column(db.String(100), unique=False, nullable=False)
    category = db.Column(db.String(40), unique=False, nullable=False)
    date_created = db.Column(db.String(50), nullable=False)
    date_updated = db.Column(db.String(50), nullable=True)
    status = db.Column(db.String(20), nullable=False)
    #    sensitive = db.Column(db.Boolean, nullable=False)
    description = db.Column(db.Text)
    pi = db.Column(db.String(50), unique=False, nullable=False)
    owner = db.Column(db.String(50), db.ForeignKey("users.public_id"), unique=False, nullable=False)
    facility = db.Column(
        db.String(50),
        db.ForeignKey("facilities.public_id"),
        unique=False,
        nullable=False,
    )
    size = db.Column(db.BigInteger, unique=False, nullable=False)
    #     size_enc = db.Column(db.BigInteger, unique=False, nullable=False)
    #     delivery_option = db.Column(db.String(10), unique=False, nullable=False)
    bucket = db.Column(db.String(100), unique=True, nullable=False)
    public_key = db.Column(db.String(64), nullable=False)
    private_key = db.Column(db.String(200), nullable=False)
    # privkey_passphrase = db.Column(
    #     db.String(64), nullable=False
    # )  # TODO (senthil, ina): put somewhere else, sensitive info and should not be in same place as private key.
    privkey_salt = db.Column(db.String(32), nullable=False)
    privkey_nonce = db.Column(db.String(24), nullable=False)

    #     # Relationships
    #     # project_s3 = db.relationship('S3Project', backref='s3_project', lazy=True,
    #     #                              foreign_keys='S3Project.project_id')
    project_files = db.relationship(
        "File", backref="file_project", lazy=True, foreign_keys="File.project_id"
    )
    #     project_tokens = db.relationship('Tokens', backref='token_project',
    #                                      lazy=True, foreign_keys='Tokens.project_id')

    def __repr__(self):
        """Called by print, creates representation of object"""

        return f"<Project {self.id}>"


# class S3Project(db.Model):
#     """Data model for S3 project info."""

#     # Table setup
#     __tablename__ = 'S3Projects'
#     __table_args__ = {'extend_existing': True}

#     # Columns
#     id = db.Column(db.String(10), primary_key=True)
#     project_id = db.Column(db.Integer, db.ForeignKey('projects.id'),
#                            unique=False, nullable=False)

#     def __repr__(self):
#         """Called by print, creates representation of object"""

#         return f'<S3Project {self.id}>'


class File(db.Model):
    """Data model for files."""

    # Table setup
    __tablename__ = "files"
    __table_args__ = {"extend_existing": True}

    #     # Columns
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(200), unique=False, nullable=False)
    name_in_bucket = db.Column(db.String(200), unique=False, nullable=False)
    subpath = db.Column(db.String(500), unique=False, nullable=False)
    size = db.Column(db.BigInteger, unique=False, nullable=False)
    size_encrypted = db.Column(db.BigInteger, unique=False, nullable=False)
    #     extension = db.Column(db.String(15), unique=False, nullable=False)
    compressed = db.Column(db.Boolean, nullable=False)
    public_key = db.Column(db.String(64), unique=False, nullable=False)
    salt = db.Column(db.String(50), unique=False, nullable=False)
    checksum = db.Column(db.String(64), unique=False, nullable=False)
    project_id = db.Column(
        db.String(32), db.ForeignKey("projects.id"), unique=False, nullable=False
    )
    date_uploaded = db.Column(db.String(50), unique=False, nullable=False)
    latest_download = db.Column(db.String(50), unique=False, nullable=True)

    def __repr__(self):
        """Called by print, creates representation of object"""

        return f"<File {self.id}>"


# THE ISSUE IS HERE -------
# TRIGGER_ProjectSize_Insert = DDL(
#     """DELIMITER $$

#     CREATE TRIGGER TRIGGER_ProjectSize_Insert
#     AFTER INSERT ON files
#     FOR EACH ROW
#     BEGIN
#         DECLARE tot_size INT;

#         SELECT SUM(size) INTO tot_size
#         FROM files WHERE project_id=new.project_id;

#         UPDATE projects
#         SET size = tot_size
#         WHERE projects.id=new.project_id;
#     END$$

#     DELIMITER ;"""
# )

# TRIGGER_ProjectSize_Update = DDL(
#     """DELIMITER $$

#     CREATE TRIGGER TRIGGER_ProjectSize_Update
#     AFTER UPDATE ON files
#     FOR EACH ROW
#     BEGIN
#         DECLARE tot_size INT;

#         SELECT SUM(size) INTO tot_size
#         FROM files WHERE project_id=new.project_id;

#         UPDATE projects
#         SET size = tot_size
#         WHERE projects.id=new.project_id;
#     END$$

#     DELIMITER ;"""
# )

# TRIGGER_ProjectSize_Delete = DDL(
#     """DELIMITER $$

#     CREATE TRIGGER TRIGGER_ProjectSize_Delete
#     AFTER DELETE ON files
#     FOR EACH ROW
#     BEGIN
#         DECLARE tot_size INT;

#         SELECT SUM(size) INTO tot_size
#         FROM files WHERE project_id=old.project_id;

#         UPDATE projects
#         SET size = tot_size
#         WHERE projects.id=old.project_id;
#     END$$

#     DELIMITER ;"""
# )

# event.listen(File, 'after_insert', TRIGGER_ProjectSize_Insert)
# event.listen(File, 'after_update', TRIGGER_ProjectSize_Update)
# event.listen(File, 'after_delete', TRIGGER_ProjectSize_Delete)
