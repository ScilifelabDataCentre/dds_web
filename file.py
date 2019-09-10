#!/usr/bin/env python3
"""file.py"""


# IMPORTS ############################################################ IMPORTS #

from __future__ import absolute_import
import sys
from datetime import date

from base import BaseHandler

# GLOBAL VARIABLES ########################################## GLOBAL VARIABLES #

MAX_STREAMED_SIZE = 1024 * 1024 * 1024


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
        proj_db = couch['projects']             # database: projects
        curr_proj = proj_db[projid]             # current project
        curr_proj_files = curr_proj['files']    # files assoc. with project

        # Save files (now uploaded)
        for fl in files:
            filename = fl['filename']

            try:
                with open(filename, "wb") as out:
                    out.write(fl['body'])
            finally:
                curr_proj_files[filename] = {
                    "size": sys.getsizeof(filename),
                    "format": filename.split(".")[-1],
                    "date_uploaded": date.today().strftime("%Y-%m-%d"),
                }

        # Save couchdb --> updated
        # and show the project page again.
        try:
            proj_db.save(curr_proj)
        finally:
            self.render('project_page.html',
                        curr_user=self.current_user,
                        projid=projid,
                        curr_project=curr_proj['project_info'],
                        files=curr_proj_files,
                        addfiles=(self.get_argument('uploadfiles', None) is not None))
