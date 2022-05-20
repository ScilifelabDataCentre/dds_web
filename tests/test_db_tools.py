# IMPORTS ################################################################################ IMPORTS #

# Standard library

# Installed
import flask
import pytest

# Own
from dds_web import db
from dds_web.database import models
from dds_web.errors import AccessDeniedError, DDSArgumentError, NoSuchProjectError
from dds_web.api import db_tools
from dds_web import auth
import tests

# TESTS #################################################################################### TESTS #

# get_project_object


def test_get_project_object_publicid_none(client):
    """Get the project object when public id is None."""
    public_id: str = None
    with pytest.raises(DDSArgumentError) as err:
        project_object: models.Project = db_tools.get_project_object(public_id=public_id)
        assert not project_object
    assert "Project ID required." in str(err.value)


def test_get_project_object_publicid_notexists(client):
    """Get project object with non existent project public_id."""
    public_id: str = "this_doesnt_exist"
    with pytest.raises(NoSuchProjectError) as err:
        project_object: models.Project = db_tools.get_project_object(public_id=public_id)
        assert not project_object
    assert "The specified project does not exist" in str(err.value)


def test_get_project_object_no_authenticated_user(client):
    """Get project object with no user logged in."""
    project = db.session.query(models.Project).first()
    public_id: str = project.public_id
    with pytest.raises(AccessDeniedError) as err:
        project_object: models.Project = db_tools.get_project_object(public_id=public_id)
        assert not project_object
    assert "No authenticated user. Project access denied." in str(err.value)


def test_get_project_object_authenticated_user_no_access(client):
    """Get project object with authenticated user with no access to the project."""
    # Create new user
    new_user = models.ResearchUser(username="new_user_for_test", password="goodpassword")
    db.session.add(new_user)
    db.session.commit()

    # Authenticate user
    # auth.current_user() calls the following
    # ref: https://github.com/miguelgrinberg/Flask-HTTPAuth/blob/b42168ed174cde0a9404dbf0b05b5b5c5d6eb46d/src/flask_httpauth.py#L185-L187
    # def current_user(self):
    #     if hasattr(g, 'flask_httpauth_user'):
    #         return g.flask_httpauth_user
    flask.g.flask_httpauth_user = new_user

    project = db.session.query(models.Project).first()
    public_id: str = project.public_id
    with pytest.raises(AccessDeniedError) as err:
        project_object: models.Project = db_tools.get_project_object(public_id=public_id)
        assert not project_object
    assert "Project access denied." in str(err.value)


def test_get_project_object_authenticated_user_success(client):
    """Get project object with authenticated user."""
    # Get project
    project = db.session.query(models.Project).first()

    # Authenticate user which we know has access to project
    # auth.current_user() calls the following
    # ref: https://github.com/miguelgrinberg/Flask-HTTPAuth/blob/b42168ed174cde0a9404dbf0b05b5b5c5d6eb46d/src/flask_httpauth.py#L185-L187
    # def current_user(self):
    #     if hasattr(g, 'flask_httpauth_user'):
    #         return g.flask_httpauth_user
    flask.g.flask_httpauth_user = project.responsible_unit.users[0]

    public_id: str = project.public_id
    project_object: models.Project = db_tools.get_project_object(public_id=public_id)
    assert project_object == project
