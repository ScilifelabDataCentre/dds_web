import marshmallow
from dds_web import utils
import pytest
from unittest.mock import patch
from dds_web import db
from dds_web.database import models
from dds_web.errors import AccessDeniedError

# contains_uppercase


def test_contains_uppercase_false():
    """Test if a lower case string contains an upper case character."""
    with pytest.raises(marshmallow.ValidationError) as err:
        utils.contains_uppercase(indata="nouppercasehere")
    assert "Required: at least one upper case letter." in str(err.value)


def test_contains_uppercase_true():
    """Test if a string contains an upper case letter."""
    utils.contains_uppercase(indata="ThereisanuppercaseInhere")


# contains_lowercase


def test_contains_lowercase_false():
    """Test if a upper case string contains a lower case character."""
    with pytest.raises(marshmallow.ValidationError) as err:
        utils.contains_lowercase(indata="NOLOWERCASEHERE")
    assert "Required: at least one lower case letter." in str(err.value)


def test_contains_lowercase_true():
    """Test if a string contains a lower case character."""
    utils.contains_lowercase(indata="ThereISALOWERCASE")


# contains_digit_or_specialchar


def test_contains_digit_or_specialchar_no_digit_or_char():
    """Test if a string without a digit or char contains a digit and char."""
    with pytest.raises(marshmallow.ValidationError) as err:
        utils.contains_digit_or_specialchar(indata="Thereisnodigitorchar")
    assert "Required: at least one digit OR a special character (#?!@$%^&*-)." in str(err.value)


def test_contains_digit_or_specialchar_no_digit():
    """Test if a string without a digit contains a digit."""
    utils.contains_digit_or_specialchar(indata="Thereisnodigitbutthereisacharhere$")


def test_contains_digit_or_specialchar_no_char():
    """Test if a string without a char contains a char."""
    utils.contains_digit_or_specialchar(indata="Thereisnodigitorchar1")


# contains_disallowed_characters


def test_contains_disallowed_characters_contains_char():
    """Test if a string contains any disallowed characters."""
    with pytest.raises(marshmallow.ValidationError) as err:
        utils.contains_disallowed_characters(indata="Also contains <")
    assert "The character '<' within" in str(err.value)
    assert "is not allowed" in str(err.value)


def test_contains_disallowed_characters_contains_multiple_char():
    """Test if a string contains any disallowed characters - multiple."""
    with pytest.raises(marshmallow.ValidationError) as err:
        utils.contains_disallowed_characters(indata="Also contains < $")
    assert "The characters '$ <' within" in str(err.value) or "The characters '< $' within" in str(
        err.value
    )
    assert "are not allowed" in str(err.value)


def test_contains_disallowed_characters():
    """Test if a string contains any disallowed characters - it doesn't."""
    utils.contains_disallowed_characters(indata="Does not contain any disallowed character")


# contains_unicode_emojis


def test_contains_unicode_emojis_true():
    """Test if a string contains any unicode emojis."""
    # Contains flag
    with pytest.raises(marshmallow.ValidationError) as err:
        utils.contains_unicode_emojis(indata="\U0001F1E0")
    assert "This input is not allowed: \U0001F1E0" in str(err.value)

    # Contains symbol
    with pytest.raises(marshmallow.ValidationError) as err:
        utils.contains_unicode_emojis(indata="\U0001F300\U0001F301")
    assert "This input is not allowed: \U0001F300\U0001F301" in str(err.value)

    # Contains emoticons
    with pytest.raises(marshmallow.ValidationError) as err:
        utils.contains_unicode_emojis(indata="\U0001F600\U0001F601")
    assert "This input is not allowed: \U0001F600\U0001F601" in str(err.value)

    # Contains transport
    with pytest.raises(marshmallow.ValidationError) as err:
        utils.contains_unicode_emojis(indata="\U0001F680\U0001F681")
    assert "This input is not allowed: \U0001F680\U0001F681" in str(err.value)

    # Contains alchemical symbols
    with pytest.raises(marshmallow.ValidationError) as err:
        utils.contains_unicode_emojis(indata="\U0001F700\U0001F701")
    assert "This input is not allowed: \U0001F700\U0001F701" in str(err.value)

    # Contains geometric shapes extended
    with pytest.raises(marshmallow.ValidationError) as err:
        utils.contains_unicode_emojis(indata="\U0001F780\U0001F781")
    assert "This input is not allowed: \U0001F780\U0001F781" in str(err.value)

    # Contains supplemental arrows-c
    with pytest.raises(marshmallow.ValidationError) as err:
        utils.contains_unicode_emojis(indata="\U0001F800\U0001F801")
    assert "This input is not allowed: \U0001F800\U0001F801" in str(err.value)

    # Contains supplemental symbols and pictographs
    with pytest.raises(marshmallow.ValidationError) as err:
        utils.contains_unicode_emojis(indata="\U0001F900\U0001F901")
    assert "This input is not allowed: \U0001F900\U0001F901" in str(err.value)

    # Contains chess symbols
    with pytest.raises(marshmallow.ValidationError) as err:
        utils.contains_unicode_emojis(indata="\U0001FA00\U0001FA01")
    assert "This input is not allowed: \U0001FA00\U0001FA01" in str(err.value)

    # Contains symbols and pictographs
    with pytest.raises(marshmallow.ValidationError) as err:
        utils.contains_unicode_emojis(indata="\U0001FA70\U0001FA71")
    assert "This input is not allowed: \U0001FA70\U0001FA71" in str(err.value)

    # Contains dingbats
    with pytest.raises(marshmallow.ValidationError) as err:
        utils.contains_unicode_emojis(indata="\U00002702\U00002703")
    assert "This input is not allowed: \U00002702\U00002703" in str(err.value)


def test_contains_unicode_emojis_false():
    """Test if a string contains any unicode emojis."""
    utils.contains_unicode_emojis(indata="Doesn't contain any emojis.")


# email_not_taken


def test_email_not_taken_true(client):
    """Check if a non taken email is taken or not."""
    utils.email_not_taken(indata="nonexistentemail@mail.com")


def test_email_not_taken_false(client):
    """Check if a taken email is taken or not."""
    from dds_web import db
    from dds_web.database import models

    user = db.session.query(models.User).first()
    with pytest.raises(marshmallow.ValidationError) as err:
        utils.email_not_taken(indata=user.primary_email)
    assert "The email is already taken by another user." in str(err.value)


# email_taken


def test_email_taken_false(client):
    """Check if a non taken email is taken or not."""
    with pytest.raises(marshmallow.ValidationError) as err:
        utils.email_taken(indata="nonexistentemail@mail.com")
    assert "If the email is connected to a user within the DDS" in str(err.value)


def test_email_taken_false(client):
    """Check if a taken email is taken or not."""
    from dds_web import db
    from dds_web.database import models

    user = db.session.query(models.User).first()
    utils.email_taken(indata=user.primary_email)


# username_not_taken


def test_username_not_taken_taken(client):
    """Check that a username is taken."""
    from dds_web import db
    from dds_web.database import models

    user = db.session.query(models.User).first()
    with pytest.raises(marshmallow.ValidationError) as err:
        utils.username_not_taken(indata=user.username)
    assert "That username is taken. Please choose a different one." in str(err.value)


def test_username_not_taken_nottaken(client):
    """Check that a username is not taken."""
    utils.username_not_taken(indata="nosuchusername")


# valid_user_role


def test_valid_user_role_false():
    """Test if a role is incorrect."""
    valid = utils.valid_user_role(specified_role="Some Role")
    assert not valid


def test_valid_user_role_false():
    """Test if a role is incorrect."""
    valid = utils.valid_user_role(specified_role="Super Admin")
    assert valid

    valid = utils.valid_user_role(specified_role="Unit Admin")
    assert valid

    valid = utils.valid_user_role(specified_role="Unit Personnel")
    assert valid

    valid = utils.valid_user_role(specified_role="Project Owner")
    assert valid

    valid = utils.valid_user_role(specified_role="Researcher")
    assert valid


# username_contains_valid_characters

# class TestForm(flask_wtf.FlaskForm):
#     """User registration form."""
#     username = wtforms.StringField(
#         "Username",
#         validators=[
#             utils.username_contains_valid_characters(),
#         ],
#     )

# def test_username_contains_valid_characters(client):
#     """"""
#     form = TestForm()
#     form.username.data = "hehej?"
#     with pytest.raises(wtforms.validators.ValidationError) as err:
#         form.validate()

# verify_enough_unit_admins

def test_verify_enough_unit_admins_less_than_2(client):
    """Verify that an exception is thrown when a unit has less than 2 unit admins."""
    # Get unit
    unit = db.session.query(models.Unit).first()
    assert unit

    # Get number of admins
    num_admins = db.session.query(models.UnitUser).filter_by(is_admin=True, unit_id=unit.id).count()
    assert num_admins == 1

    # Run function
    with pytest.raises(AccessDeniedError) as err:
        utils.verify_enough_unit_admins(unit_id=unit.id)
    assert "Your unit does not have enough Unit Admins" in str(err.value)

def test_verify_enough_unit_admins_less_than_3(client):
    """Verify that an error message is returned when a unit has less than 3 unit admins."""
    # Unit ID
    unit_id = 1

    # Get unit
    unit = db.session.query(models.Unit).filter_by(id=unit_id).one_or_none()
    assert unit

    # Get number of admins
    num_admins = db.session.query(models.UnitUser).filter_by(is_admin=True, unit_id=unit_id).count()
    assert num_admins == 1

    # Create another unit admin
    from tests import test_project_creation
    test_project_creation.create_unit_admins(num_admins=1, unit_id=unit_id)

    # Get number of admins
    num_admins = db.session.query(models.UnitUser).filter_by(is_admin=True, unit_id=unit_id).count()
    assert num_admins == 2

    # Run function
    response = utils.verify_enough_unit_admins(unit_id=unit_id)
    assert "Your unit only has 2 Unit Admins. This poses a high risk of data loss" in response

def test_verify_enough_unit_admins_ok(client):
    """Verify that no exception is thrown and no error is returned if there are at least 3 unit admins."""
    # Unit ID
    unit_id = 1

    # Get unit
    unit = db.session.query(models.Unit).filter_by(id=unit_id).one_or_none()
    assert unit

    # Get number of admins
    num_admins = db.session.query(models.UnitUser).filter_by(is_admin=True, unit_id=unit_id).count()
    assert num_admins == 1

    # Create another unit admin
    from tests import test_project_creation
    test_project_creation.create_unit_admins(num_admins=2, unit_id=unit_id)

    # Get number of admins
    num_admins = db.session.query(models.UnitUser).filter_by(is_admin=True, unit_id=unit_id).count()
    assert num_admins == 3

    # Run function
    response = utils.verify_enough_unit_admins(unit_id=unit_id)
    assert not response