####################################################################################################
# IMPORTS ################################################################################ IMPORTS #
####################################################################################################

# Standard library

# Installed
import flask
import flask_restful
import collections

# Own modules
from dds_web.api import user
from dds_web.api import project
from dds_web.api import s3
from dds_web.api import files
from dds_web.api.errors import error_codes

####################################################################################################
# BLUEPRINTS ########################################################################## BLUEPRINTS #
####################################################################################################

api_blueprint = flask.Blueprint("api_blueprint", __name__)
api = flask_restful.Api(api_blueprint, errors=error_codes)

####################################################################################################
# RESOURCES ############################################################################ RESOURCES #
####################################################################################################

# Login/access ###################################################################### Login/access #
api.add_resource(user.Token, "/user/token", endpoint="token")
api.add_resource(user.EncryptedToken, "/user/encrypted_token", endpoint="encrypted_token")

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

# User management ################################################################ User management #
api.add_resource(user.AddUser, "/user/add", endpoint="add_user")
api.add_resource(user.DeleteUser, "/user/delete", endpoint="delete_user")
api.add_resource(user.DeleteUserSelf, "/user/delete_self", endpoint="delete_user_self")

# Invoicing ############################################################################ Invoicing #
api.add_resource(user.InvoiceUnit, "/invoice", endpoint="invoice")
api.add_resource(user.ShowUsage, "/usage", endpoint="usage")
