"""Data models."""
from . import db
from sqlalchemy import func, DDL


class User(db.Model):
    """Data model for user accounts."""

    __tablename__ = 'Users'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), unique=False, nullable=False)
    last_name = db.Column(db.String(50), unique=False, nullable=False)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(120), unique=False, nullable=False)
    settings = db.Column(db.String(50), unique=False, nullable=False)
    email = db.Column(db.String(80), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=False, nullable=True)
    admin = db.Column(db.Boolean, unique=False, nullable=False)
    projects = db.relationship('Project', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'


class Facility(db.Model):
    """Data model for facility accounts."""

    __tablename__ = 'Facilities'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    internal_ref = db.Column(db.String(10), unique=True, nullable=False)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(120), unique=False, nullable=False)
    settings = db.Column(db.String(50), unique=False, nullable=False)
    email = db.Column(db.String(80), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=False, nullable=True)
    projects = db.relationship('Project', backref='facility', lazy=True)

    def __repr__(self):
        return f'<Facility {self.username}>'


class Project(db.Model):
    """Data model for projects."""

    __tablename__ = 'Projects'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), unique=False, nullable=False)
    category = db.Column(db.String(40), unique=False, nullable=False)
    order_date = db.Column(db.DateTime, nullable=False)
    delivery_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), nullable=False)
    sensitive = db.Column(db.Boolean, nullable=False)
    description = db.Column(db.Text)
    pi = db.Column(db.String(50), unique=False, nullable=False)
    owner = db.Column(db.Integer, db.ForeignKey('user.id'),
                      unique=False, nullable=False)
    facility = db.Column(db.Integer, db.ForeignKey('facility.id'),
                         unique=False, nullable=False)
    size = db.Column(db.Integer, unique=False, nullable=False)
    delivery_option = db.Column(db.String(10), unique=False, nullable=False)
    public_key = db.Column(db.String(64), nullable=False)
    private_key = db.Column(db.String(200), nullable=False)
    nonce = db.Column(db.String(24), nullable=False)
    s3_projects = db.relationship('S3Project', backref='project', lazy=True)
    files = db.relationship('File', backref='project', lazy=True)

    def __repr__(self):
        return f'<Project {self.id}>'


class S3Project(db.Model):
    """Data model for S3 project info."""

    __tablename__ = 'S3Projects'
    id = db.Column(db.String(10), primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'),
                           unique=False, nullable=False)

    def __repr__(self):
        return f'<S3Project {self.id}>'


class File(db.Model):
    """Data model for files."""

    __tablename__ = 'Files'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    directory_path = db.Column(db.String(500), unique=False, nullable=False)
    size = db.Column(db.Integer, unique=False, nullable=False)
    format = db.Column(db.String(10))
    compressed = db.Column(db.Boolean, nullable=False)
    public_key = db.Column(db.String(64), unique=False, nullable=False)
    salt = db.Column(db.String(50), unique=False, nullable=False)
    date_uploaded = db.Column(db.DateTime, unique=False, nullable=False,
                              server_default=func.now())
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'),
                           unique=False, nullable=False)


TRIGGER_ProjectSize_Insert = DDL(
    """DELIMITER $$

    CREATE TRIGGER project_size_insert
    AFTER INSERT ON Files
    FOR EACH ROW
    BEGIN
        DECLARE tot_size INT;

        SELECT SUM(size) INTO tot_size
        FROM Files WHERE project_id=new.project_id;

        UPDATE Projects
        SET size = tot_size
        WHERE Projects.id=new.project_id;
    END$$

    DELIMITER ;"""
)

TRIGGER_ProjectSize_Update = DDL(
    """DELIMITER $$

    CREATE TRIGGER TRIGGER_ProjectSize_Update
    AFTER UPDATE ON Files
    FOR EACH ROW
    BEGIN
        DECLARE tot_size INT;

        SELECT SUM(size) INTO tot_size
        FROM Files WHERE project_id=new.project_id;

        UPDATE Projects
        SET size = tot_size
        WHERE Projects.id=new.project_id;
    END$$

    DELIMITER ;"""
)

TRIGGER_ProjectSize_Delete = DDL(
    """DELIMITER $$

    CREATE TRIGGER project_size_delete
    AFTER DELETE ON Files
    FOR EACH ROW
    BEGIN
        DECLARE tot_size INT;

        SELECT SUM(size) INTO tot_size
        FROM Files WHERE project_id=old.project_id;

        UPDATE Projects
        SET size = tot_size
        WHERE Projects.id=old.project_id;
    END$$

    DELIMITER ;"""
)