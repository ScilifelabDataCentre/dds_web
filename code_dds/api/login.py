import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from datetime import datetime

from code_dds.models import Facility, User, Project, S3Project, Tokens
from code_dds import db, C_TZ



def cloud_access(project):
    '''Gets the S3 project ID (bucket ID).

    Args:
        project:    Specified project ID used in current delivery

    Returns:
        tuple:  access, s3 project ID and error message
    '''

    # Get s3 info if project in database
    s3_info = S3Project.query.filter_by(project_id=project).first()

    # Return error if s3 info not found
    if s3_info is None:
        return False, "", "There is no recorded S3 project for the specified project"

    # Access granted, S3 ID and no error message
    return True, s3_info.id, ""


def ds_access(username, password, role) -> (bool, int, str):
    '''Finds facility in db and validates the password given by user.

    Args:
        username:   The users username
        password:   The users password

    Returns:
        tuple:  If access to DS granted, facility/user ID and error message

    '''
    if role == 1:
        table = Facility
    elif role == 0:
        table = User
    else:
        pass    # custom error here?
    
    print(table, flush=True)

    # Get user from database
    user = table.query.filter_by(username=username).first()
    # Return error if username doesn't exist in database
    if user is None:
        return False, 0, "The user does not exist"

    # Get password info in response and
    # calculate secure password hash with Scrypt
    sec_pw = secure_password_hash(password_settings=user.settings,
                                  password_entered=password)

    # Return error if the password doesn't match
    if sec_pw != user.password:
        return False, 0, "Incorrect password!"

    return True, user.id, ""


def project_access(uid, project, owner) -> (bool, str):
    '''Checks the users access to the specified project

    Args:
        id:     Facility ID
        project:    Project ID
        owner:      Owner ID

    Returns:
        tuple:  access and error message
    '''

    # Get project info if owner and facility matches
    project_info = Project.query.filter_by(id=project, owner=owner,
                                           facility=uid).first()

    # Return error if project not found
    if project_info is None:
        return False, None, "The project doesn't exist or you don't have access"

    # Return error if project doesn't have access to S3
    if project_info.delivery_option != "S3":
        return False, None, "The project does not have S3 access"

    # Check length of public key and quit if wrong
    # ---- here ----

    return True, project_info.public_key, ""


def secure_password_hash(password_settings: str,
                         password_entered: str) -> (str):
    '''Generates secure password hash.

    Args:
            password_settings:  String containing the salt, length of hash,
                                n-exponential, r and p variables.
                                Taken from database. Separated by '$'.
            password_entered:   The user-specified password.

    Returns:
            str:    The derived hash from the user-specified password.

    '''

    # Split scrypt settings into parts
    settings = password_settings.split("$")
    for i in [1, 2, 3, 4]:
        settings[i] = int(settings[i])  # Set settings as int, not str

    # Create cryptographically secure password hash
    kdf = Scrypt(salt=bytes.fromhex(settings[0]),
                 length=settings[1],
                 n=2**settings[2],
                 r=settings[3],
                 p=settings[4],
                 backend=default_backend())

    return (kdf.derive(password_entered.encode('utf-8'))).hex()

def gen_access_token(project, length: int = 16):

    token = os.urandom(length).hex()
    curr_token = Tokens.query.filter_by(token=token).first()
    while curr_token is not None:
        token = os.urandom(length).hex()
        curr_token = Tokens.query.filter_by(token=token).first()
    
    new_token = Tokens(token=token, project_id=project)
    db.session.add(new_token)
    db.session.commit()

    return token

def validate_token(created, expires):
    print(f"created: {created}", flush=True)
    print(f"expires: {expires}", flush=True)

    validated = False
    # date_time_str = '18/09/19 01:55:19'
    try: 
        date_time_created = datetime.strptime(created, '%Y-%m-%d %H:%M:%S.%f%z')
    except Exception as e:
        print(e, flush=True)
    else:
        print(date_time_created, flush=True)
    date_time_expires = datetime.strptime(expires, '%Y-%m-%d %H:%M:%S.%f%z')

    print(f"created: {date_time_created}", flush=True)
    print(f"expires: {date_time_expires}", flush=True)

    now = datetime.now(tz=C_TZ)
    print(f"now: {now}", flush=True)

    if date_time_created < now < date_time_expires:
        validated = True
    
    return validated

    print(f"checking if in interval: {date_time_created < now < date_time_expires}", flush=True)