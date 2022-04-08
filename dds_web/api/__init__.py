####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library

# Installed
import flask
import flask_restful

# Own modules
from dds_web.api import user
from dds_web.api import project
from dds_web.api import s3
from dds_web.api import files
from dds_web.api import unit

####################################################################################################
# BLUEPRINTS ########################################################################## BLUEPRINTS #
####################################################################################################

api_blueprint = flask.Blueprint("api_blueprint", __name__)
api = flask_restful.Api(api_blueprint)


@api.representation("application/json")
def output_json(data, code, headers=None):
    resp = flask.make_response(flask.json.dumps(data), code)
    resp.headers.extend(headers or {})
    return resp


####################################################################################################
# RESOURCES ############################################################################ RESOURCES #
####################################################################################################

# Login/access ###################################################################### Login/access #
api.add_resource(user.EncryptedToken, "/user/encrypted_token", endpoint="encrypted_token")
api.add_resource(user.SecondFactor, "/user/second_factor", endpoint="second_factor")

# S3 ########################################################################################## S3 #
api.add_resource(s3.S3Info, "/s3/proj", endpoint="proj_s3_info")

# Files #################################################################################### Files #
api.add_resource(files.NewFile, "/file/new", endpoint="new_file")
api.add_resource(files.MatchFiles, "/file/match", endpoint="match_files")
api.add_resource(files.ListFiles, "/files/list", endpoint="list_files")
api.add_resource(files.RemoveFile, "/file/rm", endpoint="remove_file")
api.add_resource(files.RemoveDir, "/file/rmdir", endpoint="remove_dir")
api.add_resource(files.FileInfo, "/file/info", endpoint="file_info")
api.add_resource(files.FileInfoAll, "/file/all/info", endpoint="all_file_info")
api.add_resource(files.UpdateFile, "/file/update", endpoint="update_file")

# Projects ############################################################################## Projects #
api.add_resource(project.UserProjects, "/proj/list", endpoint="list_projects")
api.add_resource(project.RemoveContents, "/proj/rm", endpoint="remove_contents")
api.add_resource(project.GetPublic, "/proj/public", endpoint="public_key")
api.add_resource(project.GetPrivate, "/proj/private", endpoint="private_key")
api.add_resource(project.CreateProject, "/proj/create", endpoint="create_project")
api.add_resource(project.ProjectUsers, "/proj/users", endpoint="list_project_users")
api.add_resource(project.ProjectStatus, "/proj/status", endpoint="project_status")
api.add_resource(project.ProjectAccess, "/proj/access", endpoint="project_access")

# User management ################################################################ User management #
api.add_resource(user.RetrieveUserInfo, "/user/info", endpoint="user_info")
api.add_resource(user.AddUser, "/user/add", endpoint="add_user")
api.add_resource(user.DeleteUser, "/user/delete", endpoint="delete_user")
api.add_resource(user.DeleteUserSelf, "/user/delete_self", endpoint="delete_user_self")
api.add_resource(user.RemoveUserAssociation, "/user/access/revoke", endpoint="revoke_from_project")
api.add_resource(user.UserActivation, "/user/activation", endpoint="user_activation")
api.add_resource(
    user.RequestTOTPActivation, "/user/request_activate_totp", endpoint="request_totp_activation"
)
api.add_resource(user.UnitUsers, "/unit/users", endpoint="unit_users")

# Units #################################################################################### Units #

api.add_resource(unit.AllUnits, "/unit/info/all", endpoint="all_units")
api.add_resource(unit.MOTD, "/unit/motd", endpoint="motd")

# Invoicing ############################################################################ Invoicing #
api.add_resource(user.ShowUsage, "/usage", endpoint="usage")
