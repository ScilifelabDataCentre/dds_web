#!/usr/bin/env python3
"""file.py"""


# IMPORTS ############################################################ IMPORTS #

from __future__ import absolute_import
import sys
import logging
from datetime import date

from base import BaseHandler
from dp_common import get_current_time

# GLOBAL VARIABLES ########################################## GLOBAL VARIABLES #


# CLASSES ############################################################ CLASSES #

class UploadHandler(BaseHandler):
    """Class. Handles the upload of the file."""

    def post(self, projid):
        """post"""

        # Checks if there are files "uploaded"
        files = []
        try:
            files = self.request.files['filesToUpload']
        except OSError:
            pass
        
        # Connects to the database
        couch = self.couch_connect()            # couchdb
        project_db = couch['project_db']        # database: projects
        curr_proj = project_db[projid]          # current project
        curr_proj_files = curr_proj['files']    # files assoc. with project

        # Save files (now uploaded)
        for file_ in files:
            filename = file_['filename']

            try:
                with open(filename, "wb") as out:
                    out.write(file_['body'])
            finally:
                curr_proj_files[filename] = {
                    "size": sys.getsizeof(filename),
                    "mime": filename.split(".")[-1],
                    "date_uploaded": get_current_time(),
                    "checksum": ""
                }

        # Save couchdb --> updated
        # and show the project page again.
        try:
            project_db.save(curr_proj)
        finally:
            self.render('project_page.html',
                        curr_user=self.current_user,
                        projid=projid,
                        curr_project=curr_proj['project_info'],
                        files=curr_proj_files,
                        addfiles=(self.get_argument('uploadfiles', None) is not None))
