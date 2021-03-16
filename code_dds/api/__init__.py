###############################################################################
# IMPORTS ########################################################### IMPORTS #
###############################################################################

# Standard library

# Installed
import flask
import flask_restful

# Own modules
from code_dds.api import user
from code_dds.api import project
from code_dds.api import s3
from code_dds.api import files
from code_dds.api.errors import errors


###############################################################################
# BLUEPRINTS ##################################################### BLUEPRINTS #
###############################################################################

api_blueprint = flask.Blueprint("api_blueprint", __name__)
api = flask_restful.Api(api_blueprint, errors=errors)


###############################################################################
# RESOURCES ####################################################### RESOURCES #
###############################################################################

# Login/access ################################################# Login/access #
api.add_resource(user.AuthenticateUser, "/user/auth", endpoint="auth")
api.add_resource(project.ProjectAccess, "/proj/auth", endpoint="proj_auth")

# S3
api.add_resource(s3.S3Info, "/s3/proj", endpoint="proj_s3_info")

# Files
api.add_resource(files.NewFile, "/file/new", endpoint="new_file")
api.add_resource(files.MatchFiles, "/file/match", endpoint="match_files")
api.add_resource(files.ListFiles, "/files/list", endpoint="list_files")
api.add_resource(files.RemoveFile, "/file/rm", endpoint="remove_file")
api.add_resource(files.RemoveDir, "/file/rmdir", endpoint="remove_dir")
api.add_resource(files.FileInfo, "/file/info", endpoint="file_info")
api.add_resource(files.FileInfoAll, "/file/all/info", endpoint="all_file_info")
api.add_resource(files.UpdateFile, "/file/update", endpoint="update_file")

# Projects
api.add_resource(project.UserProjects, "/proj/list", endpoint="list_projects")
api.add_resource(project.RemoveContents, "/proj/rm", endpoint="remove_contents")
