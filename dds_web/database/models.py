"""Database table models."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library
import datetime
import base64
import os

# Installed
from sqlalchemy.ext import hybrid
import sqlalchemy
import flask
import argon2
import pyotp
import flask_login
import pathlib
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from cryptography.hazmat.primitives import twofactor
from cryptography.hazmat.primitives import hashes

# Own modules
from dds_web import db, auth
from dds_web.api.errors import AuthenticationError
import dds_web.utils


####################################################################################################
# MODELS ################################################################################## MODELS #
####################################################################################################

####################################################################################################
# Association objects ######################################################## Association objects #


class ProjectUsers(db.Model):
    """
    Many-to-many association table between projects and research users.

    Primary key(s):
    - project_id
    - user_id

    Foreign key(s):
    - project_id
    - user_id
    """

    # Table setup
    __tablename__ = "projectusers"

    # Foreign keys & relationships
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    project = db.relationship("Project", back_populates="researchusers")
    # ---
    user_id = db.Column(
        db.String(50), db.ForeignKey("researchusers.username", ondelete="CASCADE"), primary_key=True
    )
    researchuser = db.relationship("ResearchUser", back_populates="project_associations")
    # ---

    # Additional columns
    owner = db.Column(db.Boolean, nullable=False, default=False, unique=False)


class ProjectStatuses(db.Model):
    """
    One-to-many table between projects and statuses. Contains all project status history.

    Primary key(s):
    - project_id
    - status

    Foreign key(s):
    - project_id
    """

    # Table setup
    __tablename__ = "projectstatuses"

    # Foreign keys & relationships
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    project = db.relationship("Project", back_populates="project_statuses")
    # ---

    # Additional columns
    status = db.Column(db.String(50), unique=False, nullable=False, primary_key=True)
    date_created = db.Column(db.DateTime(), nullable=False, primary_key=True)

    # Columns
    is_aborted = db.Column(db.Boolean, nullable=True, default=False, unique=False)
    deadline = db.Column(db.DateTime(), nullable=True)


####################################################################################################
# Tables ################################################################################## Tables #


class Unit(db.Model):
    """
    Data model for SciLifeLab Units.

    Primary key(s):
    - id
    """

    # Table setup
    __tablename__ = "units"
    __table_args__ = {"extend_existing": True}

    # Columns
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    public_id = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), unique=True, nullable=False)
    external_display_name = db.Column(db.String(255), unique=False, nullable=False)
    contact_email = db.Column(db.String(255), unique=False, nullable=True)
    internal_ref = db.Column(db.String(50), unique=True, nullable=False)
    safespring_endpoint = db.Column(
        db.String(255), unique=False, nullable=False
    )  # unique=True later
    safespring_name = db.Column(db.String(255), unique=False, nullable=False)  # unique=True later
    safespring_access = db.Column(db.String(255), unique=False, nullable=False)  # unique=True later
    safespring_secret = db.Column(db.String(255), unique=False, nullable=False)  # unique=True later
    days_in_available = db.Column(db.Integer, unique=False, nullable=False, default=90)
    counter = db.Column(db.Integer, unique=False, nullable=True)
    days_in_expired = db.Column(db.Integer, unique=False, nullable=False, default=30)

    # Relationships
    users = db.relationship("UnitUser", back_populates="unit")
    projects = db.relationship("Project", back_populates="responsible_unit")
    invites = db.relationship(
        "Invite", back_populates="unit", passive_deletes=True, cascade="all, delete"
    )

    def __repr__(self):
        """Called by print, creates representation of object"""
        return f"<Unit {self.public_id}>"


class Project(db.Model):
    """
    Data model for projects.

    Primary key(s):
    - id

    Foreign key(s):
    - unit_id
    - created_by
    """

    # Table setup
    __tablename__ = "projects"
    __table_args__ = {"extend_existing": True}

    # Columns
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    public_id = db.Column(db.String(255), unique=True, nullable=True)
    title = db.Column(db.Text, unique=False, nullable=True)
    date_created = db.Column(
        db.DateTime(),
        nullable=True,
        default=dds_web.utils.current_time(),
    )
    date_updated = db.Column(db.DateTime(), nullable=True)
    description = db.Column(db.Text)
    pi = db.Column(db.String(255), unique=False, nullable=True)
    bucket = db.Column(db.String(255), unique=True, nullable=False)
    public_key = db.Column(db.String(64), nullable=True)
    private_key = db.Column(db.String(255), nullable=True)
    privkey_salt = db.Column(db.String(32), nullable=True)
    privkey_nonce = db.Column(db.String(24), nullable=True)
    is_sensitive = db.Column(db.Boolean, unique=False, nullable=True, default=False)
    released = db.Column(db.DateTime(), nullable=True)
    is_active = db.Column(db.Boolean, unique=False, nullable=False, default=True, index=True)

    # Foreign keys & relationships
    unit_id = db.Column(db.Integer, db.ForeignKey("units.id", ondelete="RESTRICT"), nullable=True)
    responsible_unit = db.relationship("Unit", back_populates="projects")
    # ---
    created_by = db.Column(db.String(50), db.ForeignKey("users.username", ondelete="SET NULL"))
    creator = db.relationship("User", backref="created_projects", foreign_keys=[created_by])
    last_updated_by = db.Column(db.String(50), db.ForeignKey("users.username", ondelete="SET NULL"))
    updator = db.relationship("User", backref="updated_projects", foreign_keys=[last_updated_by])
    # ---

    # Additional relationships
    files = db.relationship("File", back_populates="project")
    file_versions = db.relationship("Version", back_populates="project")
    project_statuses = db.relationship(
        "ProjectStatuses", back_populates="project", passive_deletes=True, cascade="all, delete"
    )
    researchusers = db.relationship(
        "ProjectUsers", back_populates="project", passive_deletes=True, cascade="all, delete"
    )

    @property
    def current_status(self):
        """Return the current status of the project"""
        return max(self.project_statuses, key=lambda x: x.date_created).status

    @property
    def has_been_available(self):
        """Return True if the project has ever been in the status Available"""
        result = False
        if len([x for x in self.project_statuses if "Available" in x.status]) > 0:
            result = True
        return result

    @property
    def times_expired(self):
        return len([x for x in self.project_statuses if "Expired" in x.status])

    @property
    def current_deadline(self):
        """Return deadline for statuses that have a deadline"""
        deadline = None
        if self.current_status in ["Available", "Expired"]:
            deadline = max(self.project_statuses, key=lambda x: x.date_created).deadline
        elif self.current_status in ["In Progress"]:
            if self.has_been_available:
                list_available = list(
                    filter(lambda x: x.status == "Available", self.project_statuses)
                )
                latest_available = max(list_available, key=lambda x: x.date_created)
                deadline = latest_available.deadline
        return deadline

    @property
    def safespring_project(self):
        """Get the safespring project name from responsible unit."""

        return self.responsible_unit.safespring

    @property
    def size(self):
        """Calculate size of project."""

        return sum([f.size_stored for f in self.files])

    @property
    def num_files(self):
        """Get number of files in project."""

        return len(self.files)

    def __repr__(self):
        """Called by print, creates representation of object"""

        return f"<Project {self.public_id}>"


@sqlalchemy.event.listens_for(Project, "before_update")
def add_before_project_update(mapper, connection, target):
    """Listen for the 'before_update' event on Project and update certain of its fields"""
    if auth.current_user():
        target.date_updated = dds_web.utils.current_time()
        target.last_updated_by = auth.current_user().username


# Users #################################################################################### Users #


class User(flask_login.UserMixin, db.Model):
    """
    Data model for user accounts - base user model for all user types.

    Primary key(s):
    - username
    """

    # Table setup
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    # Columns
    username = db.Column(db.String(50), primary_key=True, autoincrement=False)
    name = db.Column(db.String(255), unique=False, nullable=True)
    _password_hash = db.Column(db.String(98), unique=False, nullable=False)
    hotp_secret = db.Column(db.LargeBinary(20), unique=False, nullable=False)
    hotp_counter = db.Column(db.BigInteger, unique=False, nullable=False, default=0)
    hotp_requested_time = db.Column(db.DateTime, unique=False, nullable=True)

    # Inheritance related, set automatically
    type = db.Column(db.String(20), unique=False, nullable=False)

    # Relationships
    identifiers = db.relationship(
        "Identifier", back_populates="user", passive_deletes=True, cascade="all, delete"
    )
    emails = db.relationship(
        "Email", back_populates="user", passive_deletes=True, cascade="all, delete"
    )

    # Delete requests if User is deleted:
    # User has requested self-deletion but is deleted by Admin before confirmation by the e-mail link.
    deletion_request = db.relationship(
        "DeletionRequest", back_populates="requester", cascade="all, delete"
    )

    __mapper_args__ = {"polymorphic_on": type}  # No polymorphic identity --> no create only user

    def __init__(self, **kwargs):
        """Init all set and update hotp_secet."""
        super(User, self).__init__(**kwargs)
        if not self.hotp_secret:
            self.hotp_secret = os.urandom(20)

    def get_id(self):
        """Get user id - in this case username. Used by flask_login."""
        return self.username

    # Password related
    @property
    def password(self):
        """Raise error if trying to access password."""
        raise AttributeError("Password is not a readable attribute.")

    @password.setter
    def password(self, plaintext_password):
        """Generate the password hash and save in db."""
        pw_hasher = argon2.PasswordHasher(hash_len=32)
        self._password_hash = pw_hasher.hash(plaintext_password)

    def verify_password(self, input_password):
        """Verifies that the specified password matches the encoded password in the database."""
        # Setup Argon2 hasher
        password_hasher = argon2.PasswordHasher(hash_len=32)

        # Verify the input password
        try:
            password_hasher.verify(self._password_hash, input_password)
        except (
            argon2.exceptions.VerifyMismatchError,
            argon2.exceptions.VerificationError,
            argon2.exceptions.InvalidHash,
        ):
            # Password hasher raises exceptions if not correct
            return False

        # Rehash password if needed, e.g. if parameters are not up to date
        if password_hasher.check_needs_rehash(self._password_hash):
            try:
                self.password = input_password
                db.session.commit()
            except sqlalchemy.exc.SQLAlchemyError as sqlerr:
                db.session.rollback()
                flask.current_app.logger.exception(sqlerr)

        # Password correct
        return True

    def get_reset_token(self, expires_sec=3600):
        """Generate token for resetting password."""
        s = Serializer(flask.current_app.config["SECRET_KEY"], expires_sec)
        return s.dumps({"user_id": self.username}).decode("utf-8")

    @staticmethod
    def verify_reset_token(token):
        """Verify that the token is valid."""
        s = Serializer(flask.current_app.config["SECRET_KEY"])
        try:
            user_id = s.loads(token)["user_id"]
        except:
            return None

        return User.query.get(user_id)

    # 2FA related
    def generate_HOTP_token(self):
        """Generate a one time password, e.g. to be sent by email.

        Counter is incremented before generating token which invalidates any previous token.
        The time when it was issued is recored to put an expiration time on the token.

        """
        self.hotp_counter += 1
        self.hotp_requested_time = dds_web.utils.current_time()
        db.session.commit()
        flask.current_app.logger.info(
            f"Incremented counter to: {self.hotp_counter} and saved time: {self.hotp_requested_time}"
        )

        hotp = twofactor.hotp.HOTP(self.hotp_secret, 8, hashes.SHA512())
        return hotp.generate(self.counter)

    def verify_HOTP(self, token):
        """Verify the HOTP token.

        raises AuthenticationError if token is invalid or has expired (older than 1 hour).
        If the token is valid, the counter is incremented, to prohibit re-use.
        """
        hotp = twofactor.hotp.HOTP(self.hotp_secret, 8, hashes.SHA512())
        if self.hotp_requested_time - dds_web.utils.current_time() > timedelta(hours=1):
            raise AuthenticationError("Email 2-factor token has expired.")

        try:
            hotp.verify(token, self.counter)
        except twofactor.InvalidToken:
            raise AuthenticationError("Invalid 2-factor token.")

        # Token verified, increment counter to prohibit re-use
        self.hotp_counter += 1
        db.session.commit()

    # Email related
    @property
    def primary_email(self):
        """Get users primary email."""
        prims = [x.email for x in self.emails if x.primary]
        return prims[0] if len(prims) > 0 else None

    def __repr__(self):
        """Called by print, creates representation of object"""

        return f"<User {self.username}>"


class ResearchUser(User):
    """
    Data model for research user accounts.

    Primary key(s):
    - username

    Foreign key(s):
    - username
    """

    __tablename__ = "researchusers"
    __mapper_args__ = {"polymorphic_identity": "researchuser"}

    # Foreign keys
    username = db.Column(
        db.String(50), db.ForeignKey("users.username", ondelete="CASCADE"), primary_key=True
    )

    # Relationships
    project_associations = db.relationship(
        "ProjectUsers", back_populates="researchuser", passive_deletes=True, cascade="all, delete"
    )

    @property
    def role(self):
        """Get user role."""

        return "Researcher"

    @property
    def projects(self):
        """Return list of project items."""

        return [proj.project for proj in self.project_associations]


class UnitUser(User):
    """
    Data model for unit user accounts.

    Primary key(s):
    - username

    Foreign key(s):
    - username
    - unit_id
    """

    __tablename__ = "unitusers"
    __mapper_args__ = {"polymorphic_identity": "unituser"}

    # Foreign keys & relationships
    username = db.Column(
        db.String(50), db.ForeignKey("users.username", ondelete="CASCADE"), primary_key=True
    )
    # ---
    unit_id = db.Column(db.Integer, db.ForeignKey("units.id", ondelete="RESTRICT"), nullable=False)
    unit = db.relationship("Unit", back_populates="users")

    # Additional columns
    is_admin = db.Column(db.Boolean, nullable=False, default=False)

    @property
    def role(self):
        """User role is Unit Admin if the unit user has admin rights."""

        if self.is_admin:
            return "Unit Admin"

        return "Unit Personnel"

    @property
    def projects(self):
        """Get the unit projects."""

        return self.unit.projects


class SuperAdmin(User):
    """
    Data model for super admin user accounts (Data Centre).

    Primary key(s):
    - username

    Foreign key(s):
    - username
    """

    __tablename__ = "superadmins"
    __mapper_args__ = {"polymorphic_identity": "superadmin"}

    # Foreign keys & relationships
    username = db.Column(db.String(50), db.ForeignKey("users.username"), primary_key=True)

    @property
    def role(self):
        """Get user role."""

        return "Super Admin"

    @property
    def projects(self):
        """Get list of projects: Super admins can access all projects."""

        return Project.query.all()


####################################################################################################


class Identifier(db.Model):
    """
    Data model for user identifiers for login.

    Elixir identifiers consists of 58 characters (40 hex + "@elixir-europe.org").

    Primary key(s):
    - username
    - identifier

    Foreign key(s):
    - username
    """

    # Table setup
    __tablename__ = "identifiers"
    __table_args__ = {"extend_existing": True}

    # Foreign keys & relationships
    username = db.Column(
        db.String(50), db.ForeignKey("users.username", ondelete="CASCADE"), primary_key=True
    )
    user = db.relationship("User", back_populates="identifiers")
    # ---

    # Additional columns
    identifier = db.Column(db.String(58), primary_key=True, unique=True, nullable=False)

    def __repr__(self):
        """Called by print, creates representation of object"""

        return f"<Identifier {self.identifier}>"


class Email(db.Model):
    """
    Data model for user email addresses.

    Primary key:
    - id

    Foreign key(s):
    - user_id
    """

    # Table setup
    __tablename__ = "emails"
    __table_args__ = {"extend_existing": True}

    # Primary keys
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Foreign keys & relationships
    user_id = db.Column(
        db.String(50), db.ForeignKey("users.username", ondelete="CASCADE"), nullable=False
    )
    user = db.relationship("User", back_populates="emails")
    # ---

    # Additional columns
    email = db.Column(db.String(254), unique=True, nullable=False)
    primary = db.Column(db.Boolean, unique=False, nullable=False, default=False)

    def __repr__(self):
        """Called by print, creates representation of object"""

        return f"<Email {self.email}>"


class Invite(db.Model):
    """
    Invites for users not yet confirmed in DDS.

    Primary key:
    - id

    Foreign key(s):
    - unit_id
    """

    # Table setup
    __tablename__ = "invites"
    __table_args__ = {"extend_existing": True}

    # Primary Key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Foreign keys & relationships
    unit_id = db.Column(db.Integer, db.ForeignKey("units.id", ondelete="CASCADE"))
    unit = db.relationship("Unit", back_populates="invites")
    # ---

    # Additional columns
    email = db.Column(db.String(254), unique=True, nullable=False)
    role = db.Column(db.String(20), unique=False, nullable=False)

    def __repr__(self):
        """Called by print, creates representation of object"""

        return f"<Invite {self.email}>"


class DeletionRequest(db.Model):
    """Table to collect self-deletion requests by users"""

    # Table setup
    __tablename__ = "deletions"
    __table_args__ = {"extend_existing": True}

    # Primary Key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    requester_id = db.Column(db.String(50), db.ForeignKey("users.username", ondelete="CASCADE"))
    requester = db.relationship("User", back_populates="deletion_request")
    email = db.Column(db.String(254), unique=True, nullable=False)
    issued = db.Column(db.DateTime(), unique=False, nullable=False)

    def __repr__(self):
        """Called by print, creates representation of object"""

        return f"<DeletionRequest {self.email}>"


class File(db.Model):
    """
    Data model for files.

    Primary key:
    - id

    Foreign key(s):
    - project_id
    """

    # Table setup
    __tablename__ = "files"
    __table_args__ = {"extend_existing": True}

    # Columns
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)

    # Foreign keys & relationships
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    project = db.relationship("Project", back_populates="files")
    # ---

    # Additional columns
    name = db.Column(db.Text, unique=False, nullable=False)
    name_in_bucket = db.Column(db.Text, unique=False, nullable=False)
    subpath = db.Column(db.Text, unique=False, nullable=False)
    size_original = db.Column(db.BigInteger, unique=False, nullable=False)
    size_stored = db.Column(db.BigInteger, unique=False, nullable=False)
    compressed = db.Column(db.Boolean, nullable=False)
    public_key = db.Column(db.String(64), unique=False, nullable=False)
    salt = db.Column(db.String(32), unique=False, nullable=False)
    checksum = db.Column(db.String(64), unique=False, nullable=False)
    time_latest_download = db.Column(db.DateTime(), unique=False, nullable=True)

    # Additional relationships
    versions = db.relationship("Version", back_populates="file")

    def __repr__(self):
        """Called by print, creates representation of object"""

        return f"<File {pathlib.Path(self.name).name}>"


class Version(db.Model):
    """
    Data model for keeping track of all active and non active files. Used for invoicing.

    Primary key:
    - id

    Foreign key(s):
    - project_id
    - active_file
    """

    # Table setup
    __tablename__ = "versions"
    __table_args__ = {"extend_existing": True}

    # Columns
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Foreign keys & relationships
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="RESTRICT"), nullable=False
    )
    project = db.relationship("Project", back_populates="file_versions")
    # ---
    active_file = db.Column(
        db.BigInteger, db.ForeignKey("files.id", ondelete="SET NULL"), nullable=True
    )
    file = db.relationship("File", back_populates="versions")
    # ---

    # Additional columns
    size_stored = db.Column(db.BigInteger, unique=False, nullable=False)
    time_uploaded = db.Column(
        db.DateTime(), unique=False, nullable=False, default=dds_web.utils.current_time()
    )
    time_deleted = db.Column(db.DateTime(), unique=False, nullable=True, default=None)
    time_invoiced = db.Column(db.DateTime(), unique=False, nullable=True, default=None)

    def __repr__(self):
        """Called by print, creates representation of object"""

        return f"<File Version {self.id}>"
