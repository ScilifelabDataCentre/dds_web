#!/usr/bin/env python3
"""project.py"""


# IMPORTS ############################################################ IMPORTS #

from __future__ import absolute_import
from base import BaseHandler

# GLOBAL VARIABLES ########################################## GLOBAL VARIABLES #

MAX_STREAMED_SIZE = 1024 * 1024 * 1024


# CLASSES ############################################################ CLASSES #

class ProjectHandler(BaseHandler):
    """Called by "See project" button.
    Connects to database and collects all files
    associated with the project and user. Renders project page."""

    def post(self, projid):
        """Sets project status to finished or open depending on which
        button is pressed on project page."""

        if ((self.get_argument('setasfinished', None) is not None)
                or (self.get_argument('setasopen', None) is not None)):
            couch = self.couch_connect()

            proj_db = couch['projects']
            curr_proj = proj_db[projid]

            if self.get_argument('setasfinished', None) is not None:
                curr_proj['project_info']['status'] = "Uploaded"
            elif self.get_argument('setasopen', None) is not None:
                curr_proj['project_info']['status'] = "Delivery in progress"

            try:
                proj_db.save(curr_proj)
            finally:
                self.render('project_page.html',
                            curr_user=self.current_user,
                            projid=projid,
                            curr_project=curr_proj['project_info'],
                            files=curr_proj['files'],
                            addfiles=(self.get_argument('uploadfiles', None) is not None))

    def get(self, projid):
        """Renders the project page with projects and associated files."""

        # Current project
        self.set_secure_cookie("project", projid, expires_days=0.1)

        # Connect to db
        couch = self.couch_connect()
        proj_db = couch['projects']

        project_info = proj_db[projid]['project_info']

        # Save project files in dict
        files = {}
        if 'files' in proj_db[projid]:
            files = proj_db[projid]['files']

        self.render('project_page.html', curr_user=self.current_user,
                    files=files, projid=projid, curr_project=project_info,
                    addfiles=(self.get_argument('uploadfiles', None) is not None))
