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

# Own modules
from dds_web import db, C_TZ
import dds_web.utils


####################################################################################################
# MODELS ################################################################################## MODELS #
####################################################################################################

# Association tables ########################################################## Association tables #


class ProjectUsers(db.Model):

    # Table setup
    __tablename__ = "projectusers"

    # Primary keys / Foreign keys
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), primary_key=True)
    user_id = db.Column(db.String(50), db.ForeignKey("researchusers.username"), primary_key=True)

    # Columns
    owner = db.Column(db.Boolean, nullable=False, default=False, unique=False)

    # Relationships - many to many
    project = db.relationship("Project", backref="researchusers")
    researchuser = db.relationship("ResearchUser", backref="project_associations")


####################################################################################################
# Tables ################################################################################## Tables #


class Unit(db.Model):
    """Data model for unit accounts."""

    # Table setup
    __tablename__ = "units"
    __table_args__ = {"extend_existing": True}

    # Primary key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Columns
    public_id = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), unique=True, nullable=False)
    external_display_name = db.Column(db.String(255), unique=False, nullable=False)
    contact_email = db.Column(db.String(255), unique=False, nullable=True)
    internal_ref = db.Column(db.String(50), unique=True, nullable=False)
    safespring = db.Column(db.String(255), unique=False, nullable=False)  # unique=True later
    days_to_expire = db.Column(db.Integer, unique=False, nullable=False, default=90)
    counter = db.Column(db.Integer, unique=False, nullable=True)

    # Relationships
    # One unit can have many users
    users = db.relationship("UnitUser", backref="unit")
    # One unit can have many projects
    projects = db.relationship("Project", backref="responsible_unit")
    # One unit can have many invites
    invites = db.relationship("Invite", backref="unit")

    def __repr__(self):
        """Called by print, creates representation of object"""
        return f"<Unit {self.public_id}>"


class Project(db.Model):
    """Data model for projects."""

    # Table setup
    __tablename__ = "projects"
    __table_args__ = {"extend_existing": True}

    # Primary key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Foreign keys
    # One project is associated to one unit. One unit can have many projects.
    unit_id = db.Column(db.Integer, db.ForeignKey("units.id"), nullable=False)

    # One project can be created by one user
    created_by = db.Column(db.String(50), db.ForeignKey("users.username"), nullable=False)

    # Columns
    public_id = db.Column(db.String(255), unique=True, nullable=False)
    title = db.Column(db.Text, unique=False, nullable=False)
    date_created = db.Column(
        db.DateTime(),
        nullable=False,
        default=dds_web.utils.current_time(),
    )
    date_updated = db.Column(db.DateTime(), nullable=True)
    status = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    pi = db.Column(db.String(255), unique=False, nullable=False)
    bucket = db.Column(db.String(255), unique=True, nullable=False)
    public_key = db.Column(db.String(64), nullable=False)
    private_key = db.Column(db.String(255), nullable=False)
    privkey_salt = db.Column(db.String(32), nullable=False)
    privkey_nonce = db.Column(db.String(24), nullable=False)
    is_sensitive = db.Column(db.Boolean, unique=False, nullable=False, default=False)

    # Relationships
    # One project can have many files
    files = db.relationship("File", backref="project")
    # One project can have many expired files
    expired_files = db.relationship("ExpiredFile", backref="assigned_project")
    # One project can have many file versions
    file_versions = db.relationship("Version", backref="responsible_project")

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


# Users #################################################################################### Users #


class User(flask_login.UserMixin, db.Model):
    """Data model for user accounts - base user model for all user types."""

    # Table setup
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}
    # Columns
    username = db.Column(db.String(50), primary_key=True, autoincrement=False)
    name = db.Column(db.String(255), unique=False, nullable=True)
    _password_hash = db.Column(db.String(98), unique=False, nullable=False)
    _otp_secret = db.Column(db.String(32))
    has_2fa = db.Column(db.Boolean)

    type = db.Column(db.String(20), unique=False, nullable=False)

    # One user can have many identifiers
    identifiers = db.relationship("Identifier", backref="user", cascade="all, delete-orphan")
    # One user can have many email addresses
    emails = db.relationship("Email", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    # One user can create many projects
    created_projects = db.relationship("Project", backref="user", cascade="all, delete-orphan")

    __mapper_args__ = {"polymorphic_on": type}  # No polymorphic identity --> no create only user

    def __init__(self, **kwargs):
        """Init all set and update otp secret."""
        super(User, self).__init__(**kwargs)
        if self.otp_secret is None:
            self.otp_secret = self.gen_otp_secret()
        self.has_2fa = False

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
        if not password_hasher.check_needs_rehash(self._password_hash):
            try:
                self.password = input_password
                db.session.commit()
            except sqlalchemy.exc.SQLAlchemyError as sqlerr:
                db.session.rollback()
                flask.current_app.logger.exception(sqlerr)

        # Password correct
        return True

    def gen_otp_secret(self):
        """Generate random base 32 for otp secret."""
        return pyotp.random_base32()

    # 2FA related
    @property
    def otp_secret(self):
        """Get OTP secret for user."""
        return self._otp_secret

    @otp_secret.setter
    def otp_secret(self, otp_secret):
        """Set new otp secret."""
        if not otp_secret:
            otp_secret = self.gen_otp_secret()
        self._otp_secret = otp_secret

    def set_2fa_seen(self):
        """Renew the otp secret -- one should only be setup once."""
        self.has_2fa = True

    def totp_uri(self):
        """Get uri for user otp_secret."""
        return pyotp.totp.TOTP(self.otp_secret).provisioning_uri(
            name=self.username, issuer_name="Data Delivery System"
        )

    def verify_totp(self, token):
        """Verify the otp token."""
        totp = pyotp.TOTP(self.otp_secret)
        return totp.verify(token)

    def __repr__(self):
        """Called by print, creates representation of object"""

        return f"<User {self.username}>"


class ResearchUser(User):
    """Data model for research user accounts."""

    __tablename__ = "researchusers"
    __mapper_args__ = {"polymorphic_identity": "researchuser"}

    # primary key and foreign key pointing to users
    username = db.Column(db.String(50), db.ForeignKey("users.username"), primary_key=True)

    @property
    def role(self):
        """Get user role."""

        return "Researcher"

    @property
    def projects(self):
        """Return list of project items."""

        return [proj.project for proj in self.project_associations]


class UnitUser(User):
    """Data model for unit user accounts"""

    __tablename__ = "unitusers"
    __mapper_args__ = {"polymorphic_identity": "unituser"}

    # Primary key and foreign key pointing to users
    username = db.Column(db.String(50), db.ForeignKey("users.username"), primary_key=True)

    # Foreign key and backref with infrastructure
    unit_id = db.Column(db.Integer, db.ForeignKey("units.id"), nullable=False)

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
    """Data model for super admin user accounts (Data Centre)."""

    __tablename__ = "superadmins"
    __mapper_args__ = {"polymorphic_identity": "superadmin"}

    # Foreign key and backref with infrastructure
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
    """

    # Table setup
    __tablename__ = "identifiers"
    __table_args__ = {"extend_existing": True}

    # Columns
    # Foreign keys
    username = db.Column(db.String(50), db.ForeignKey("users.username"), primary_key=True)
    identifier = db.Column(db.String(58), primary_key=True, unique=True, nullable=False)

    def __repr__(self):
        """Called by print, creates representation of object"""

        return f"<Identifier {self.identifier}>"


class Email(db.Model):
    """Data model for user email addresses."""

    # Table setup
    __tablename__ = "emails"
    __table_args__ = {"extend_existing": True}

    # Columns
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Foreign key: One user can have multiple email addresses.
    user_id = db.Column(db.String(50), db.ForeignKey("users.username"))

    email = db.Column(db.String(254), unique=True, nullable=False)
    primary = db.Column(db.Boolean, unique=False, nullable=False, default=False)

    def __repr__(self):
        """Called by print, creates representation of object"""

        return f"<Email {self.email}>"


class Invite(db.Model):
    """Invites for users not yet confirmed in DDS"""

    # Table setup
    __tablename__ = "invites"
    __table_args__ = {"extend_existing": True}

    # Primary Key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Foreign key
    unit_id = db.Column(db.Integer, db.ForeignKey("units.id"))

    # Columns
    email = db.Column(db.String(254), unique=True, nullable=False)
    role = db.Column(db.String(20), unique=False, nullable=False)

    def __repr__(self):
        """Called by print, creates representation of object"""

        return f"<Invite {self.email}>"


class File(db.Model):
    """Data model for files."""

    # Table setup
    __tablename__ = "files"
    __table_args__ = {"extend_existing": True}

    # Columns
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)

    # Foreign keys: One project can have many files
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), index=True)

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
    expires = db.Column(
        db.DateTime(),
        unique=False,
        nullable=False,
        default=dds_web.utils.current_time() + datetime.timedelta(days=30),
    )

    # Relationships
    versions = db.relationship("Version", backref="file")

    def __repr__(self):
        """Called by print, creates representation of object"""

        return f"<File {pathlib.Path(self.name).name}>"


class ExpiredFile(db.Model):
    """Data model for expired files. Moved here when in system for more than a month."""

    # Table setup
    __tablename__ = "expired_files"
    __table_args__ = {"extend_existing": True}

    # Columns
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

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
    expired = db.Column(
        db.DateTime(),
        unique=False,
        nullable=False,
        default=dds_web.utils.current_time(),
    )

    # Foreign keys
    # One project can have many files
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"))

    def __repr__(self):
        """Called by print, creates representation of object"""

        return f"<ExpiredFile {pathlib.Path(self.name).name}: {self.expired}>"


class Version(db.Model):
    """Data model for keeping track of all active and non active files. Used for invoicing."""

    # Table setup
    __tablename__ = "versions"
    __table_args__ = {"extend_existing": True}

    # Columns
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Foreign key - One project can have many files
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )

    # Foreign key - One file can have many rows in invoicing
    active_file = db.Column(
        db.BigInteger, db.ForeignKey("files.id", ondelete="SET NULL"), nullable=True
    )

    size_stored = db.Column(db.BigInteger, unique=False, nullable=False)
    time_uploaded = db.Column(
        db.DateTime(), unique=False, nullable=False, default=dds_web.utils.current_time()
    )
    time_deleted = db.Column(db.DateTime(), unique=False, nullable=True, default=None)
    time_invoiced = db.Column(db.DateTime(), unique=False, nullable=True, default=None)

    def __repr__(self):
        """Called by print, creates representation of object"""

        return f"<File Version {self.id}>"
