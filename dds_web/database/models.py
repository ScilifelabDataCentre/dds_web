"""Database table models."""

####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library
import datetime
import os
import time

# Installed
import sqlalchemy
import flask
import argon2
import flask_login
import pathlib
from cryptography.hazmat.primitives.twofactor import (
    hotp as twofactor_hotp,
    totp as twofactor_totp,
    InvalidToken as twofactor_InvalidToken,
)
from cryptography.hazmat.primitives import hashes

# Own modules
from dds_web import db, auth
from dds_web.errors import AuthenticationError
from dds_web.security.project_user_keys import generate_user_key_pair
import dds_web.utils


####################################################################################################
# MODELS ################################################################################## MODELS #
####################################################################################################

####################################################################################################
# Association objects ######################################################## Association objects #


class ProjectUserKeys(db.Model):
    """
    Many-to-many association table between projects and users (all).

    Primary key(s):
    - project_id
    - user_id

    Foreign key(s):
    - project_id
    - user_id
    """

    # Table setup
    __tablename__ = "projectuserkeys"

    # Foreign keys & relationships
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    project = db.relationship("Project", back_populates="project_user_keys")
    # ---
    user_id = db.Column(
        db.String(50), db.ForeignKey("users.username", ondelete="CASCADE"), primary_key=True
    )
    user = db.relationship("User", back_populates="project_user_keys")
    # ---

    # Additional columns
    key = db.Column(db.LargeBinary(300), nullable=False, unique=True)


class ProjectInviteKeys(db.Model):
    """
    Many-to-many association table between projects and invites.

    Primary key(s):
    - project_id
    - invite_id

    Foreign key(s):
    - project_id
    - invite_id
    """

    # Table setup
    __tablename__ = "projectinvitekeys"

    # Foreign keys & relationships
    project_id = db.Column(
        db.Integer, db.ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    project = db.relationship("Project", back_populates="project_invite_keys")
    # ---
    invite_id = db.Column(
        db.Integer, db.ForeignKey("invites.id", ondelete="CASCADE"), primary_key=True
    )
    invite = db.relationship("Invite", back_populates="project_invite_keys")
    # ---

    # Additional columns
    key = db.Column(db.LargeBinary(300), nullable=False, unique=True)
    owner = db.Column(db.Boolean, nullable=False, default=False, unique=False)


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
    public_key = db.Column(db.LargeBinary(100), nullable=True)

    non_sensitive = db.Column(db.Boolean, unique=False, default=False, nullable=False)
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
    project_user_keys = db.relationship(
        "ProjectUserKeys", back_populates="project", passive_deletes=True
    )
    project_invite_keys = db.relationship(
        "ProjectInviteKeys", back_populates="project", passive_deletes=True
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

    def __str__(self):
        """Called by str(), creates representation of object"""

        return f"Project {self.public_id}"

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
    # 2fa columns
    hotp_secret = db.Column(db.LargeBinary(20), unique=False, nullable=False)
    hotp_counter = db.Column(db.BigInteger, unique=False, nullable=False, default=0)
    hotp_issue_time = db.Column(db.DateTime, unique=False, nullable=True)
    totp_enabled = db.Column(db.Boolean, unique=False, nullable=False, default=False)
    _totp_secret = db.Column(db.LargeBinary(64), unique=False, nullable=True)
    totp_last_verified = db.Column(db.DateTime, unique=False, nullable=True)
    
    active = db.Column(db.Boolean, nullable=False, default=True)
    
    kd_salt = db.Column(db.LargeBinary(32), default=None)
    nonce = db.Column(db.LargeBinary(12), default=None)
    public_key = db.Column(db.LargeBinary(300), default=None)
    private_key = db.Column(db.LargeBinary(300), default=None)

    # Inheritance related, set automatically
    type = db.Column(db.String(20), unique=False, nullable=False)

    # Relationships
    identifiers = db.relationship(
        "Identifier", back_populates="user", passive_deletes=True, cascade="all, delete"
    )
    emails = db.relationship(
        "Email", back_populates="user", passive_deletes=True, cascade="all, delete"
    )
    project_user_keys = db.relationship(
        "ProjectUserKeys", back_populates="user", passive_deletes=True
    )

    # Delete requests if User is deleted:
    # User has requested self-deletion but is deleted by Admin before confirmation by the e-mail link.
    deletion_request = db.relationship(
        "DeletionRequest", back_populates="requester", cascade="all, delete"
    )
    password_reset = db.relationship("PasswordReset", back_populates="user", cascade="all, delete")

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

        # User key pair should only be set from here if the password is lost
        # and all the keys associated with the user should be cleaned up
        # before setting the password.
        # This should help the tests for setup as well.
        if not self.public_key or not self.private_key:
            self.kd_salt = os.urandom(32)
            generate_user_key_pair(self, plaintext_password)

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

    # 2FA related
    def generate_HOTP_token(self):
        """Generate a one-time authentication code, e.g. to be sent by email.

        Counter is incremented before generating token which invalidates any previous token.
        The time when it was issued is recorded to put an expiration time on the token.

        """
        self.hotp_counter += 1
        self.hotp_issue_time = dds_web.utils.current_time()
        db.session.commit()

        hotp = twofactor_hotp.HOTP(self.hotp_secret, 8, hashes.SHA512())
        return hotp.generate(self.hotp_counter)

    def reset_current_HOTP(self):
        """Make the previous HOTP as invalid by nulling issue time and increasing counter."""
        self.hotp_issue_time = None
        self.hotp_counter += 1

    def verify_HOTP(self, token):
        """Verify the HOTP token.

        raises AuthenticationError if token is invalid or has expired (older than 1 hour).
        If the token is valid, the counter is incremented, to prohibit re-use.
        """
        hotp = twofactor_hotp.HOTP(self.hotp_secret, 8, hashes.SHA512())
        if self.hotp_issue_time is None:
            raise AuthenticationError("No one-time authentication code currently issued.")
        timediff = dds_web.utils.current_time() - self.hotp_issue_time
        if timediff > datetime.timedelta(minutes=15):
            raise AuthenticationError("One-time authentication code has expired.")

        try:
            hotp.verify(token, self.hotp_counter)
        except twofactor_InvalidToken as exc:
            raise AuthenticationError("Invalid one-time authentication code.") from exc

        # Token verified, increment counter to prohibit re-use
        self.hotp_counter += 1
        # Reset the hotp_issue_time to allow a new code to be issued
        self.hotp_issue_time = None
        db.session.commit()

    @property
    def totp_initiated(self):
        """To check if activation of TOTP has been initiated, not to be confused
        with user.totp_enabled, that indicates if TOTP is successfully enabled for the user."""
        return self._totp_secret is not None

    def totp_object(self):
        """Google Authenticator seems to only be able to handle SHA1 and 6 digit codes"""
        if self.totp_initiated:
            return twofactor_totp.TOTP(self._totp_secret, 6, hashes.SHA1(), 30)
        return None

    def setup_totp_secret(self):
        """Generate random 160 bit as the new totp secret and return provisioning URI
        We're using SHA1 (Google Authenticator seems to only use SHA1 and 6 digit codes)
        so secret should be at least 160 bits
        https://cryptography.io/en/latest/hazmat/primitives/twofactor/#cryptography.hazmat.primitives.twofactor.totp.TOTP
        """
        self._totp_secret = os.urandom(20)
        db.session.commit()

    def get_totp_secret(self):
        """Returns the users totp provisioning URI. Can only be sent before totp has been enabled."""
        if self.totp_enabled:
            # Can not be fetched again after it has been enabled
            raise AuthenticationError("TOTP secret already enabled.")
        totp = self.totp_object()

        return self._totp_secret, totp.get_provisioning_uri(
            account_name=self.username,
            issuer="Data Delivery System",
        )

    def activate_totp(self):
        """Set TOTP as the preferred means of second factor authentication.
        Should be called after first totp token is verified
        """
        self.totp_enabled = True
        db.session.commit()

    def verify_TOTP(self, token):
        """Verify the totp token. Checks the previous, current and comming time frame
        to allow for some clock drift.

        raises AuthenticationError if token is invalid, has expired or
        if totp has been successfully verified within the last 90 seconds.
        """
        # can't use totp successfully more than once within 90 seconds.
        # Time frame chosen so that no one can use the same token more than once
        # No need to use epoch time here.
        current_time = dds_web.utils.current_time()
        if self.totp_last_verified is not None and (
            current_time - self.totp_last_verified < datetime.timedelta(seconds=90)
        ):
            raise AuthenticationError(
                "Authentication with TOTP needs to be at least 90 seconds apart."
            )

        # construct object
        totp = self.totp_object()

        # attempt to verify the token using epoch time
        # Allow for clock drift of 1 frame before or after
        verified = False
        for t_diff in [-30, 0, 30]:
            verification_time = time.time() + t_diff
            try:
                totp.verify(token, verification_time)
                verified = True
                break
            except twofactor_InvalidToken:
                pass

        if not verified:
            raise AuthenticationError("Invalid TOTP token.")

        # if the token is valid, save time of last successful verification
        self.totp_last_verified = current_time
        db.session.commit()

    # Email related
    @property
    def primary_email(self):
        """Get users primary email."""
        prims = [x.email for x in self.emails if x.primary]
        return prims[0] if len(prims) > 0 else None

    @property
    def is_active(self):
        return self.active

    def __str__(self):
        """Called by str(), creates representation of object"""

        return f"User {self.username}"

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
    project_invite_keys = db.relationship(
        "ProjectInviteKeys", back_populates="invite", passive_deletes=True, cascade="all, delete"
    )
    # ---

    # Additional columns
    email = db.Column(db.String(254), unique=True, nullable=False)
    role = db.Column(db.String(20), unique=False, nullable=False)
    nonce = db.Column(db.LargeBinary(12), default=None)
    public_key = db.Column(db.LargeBinary(300), default=None)
    private_key = db.Column(db.LargeBinary(300), default=None)

    @property
    def projects(self):
        """Return list of project items."""

        return [proj.project for proj in self.project_associations]

    def __str__(self):
        """Called by str(), creates representation of object"""

        return f"Pending invite for {self.email}"

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


class PasswordReset(db.Model):
    """Keep track of password resets."""

    # Table setup
    __tablename__ = "password_resets"
    __table_args__ = {"extend_existing": True}

    # Primary Key
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    user_id = db.Column(db.String(50), db.ForeignKey("users.username", ondelete="CASCADE"))
    user = db.relationship("User", back_populates="password_reset")

    email = db.Column(db.String(254), unique=True, nullable=False)
    issued = db.Column(db.DateTime(), unique=False, nullable=False)
    changed = db.Column(db.DateTime(), unique=False, nullable=True)

    valid = db.Column(db.Boolean, unique=False, nullable=False, default=True)


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


class MOTD(db.Model):
    """
    Data model for keeping track of MOTD (message of the day).

    Primary key:
    - message
    """

    # Table setup
    __tablename__ = "motd"
    __table_args__ = {"extend_existing": True}

    # Columns
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    message = db.Column(db.Text, nullable=False, default=None)
    date_created = db.Column(db.DateTime(), nullable=False, default=None)
