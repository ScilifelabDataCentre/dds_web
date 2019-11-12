#!/usr/bin/env python3
"""project.py"""


# IMPORTS ############################################################ IMPORTS #

from __future__ import absolute_import
from base import BaseHandler

# GLOBAL VARIABLES ########################################## GLOBAL VARIABLES #


# CLASSES ############################################################ CLASSES #

class ProjectStatus(BaseHandler):
    """docstring"""

    def post(self, projid):
        """docstring"""

        if ((self.get_argument('setasfinished', None) is not None)
                or (self.get_argument('setasopen', None) is not None)):
            couch = self.couch_connect()

            project_db = couch['project_db']
            curr_proj = project_db[projid]

            if self.get_argument('setasfinished', None) is not None:
                curr_proj['project_info']['status'] = "Finished"
            elif self.get_argument('setasopen', None) is not None:
                curr_proj['project_info']['status'] = "Ongoing"

            try:
                project_db.save(curr_proj)
            finally:
                self.render('project_page.html',
                            curr_user=self.current_user,
                            projid=projid,
                            curr_project=curr_proj['project_info'],
                            files=curr_proj['files'],
                            addfiles=(self.get_argument('uploadfiles', None) is not None))


class ProjectHandler(BaseHandler):
    """Called by "See project" button.
    Connects to database and collects all files
    associated with the project and user. Renders project page."""

    def get(self, projid):
        """Renders the project page with projects and associated files."""

        # Connect to db
        couch = self.couch_connect()
        project_db = couch['project_db']

        project_info = project_db[projid]['project_info']

        # Save project files in dict
        files = {}
        if 'files' in project_db[projid]:
            files = project_db[projid]['files']
        
        self.render('project_page.html', curr_user=self.current_user,
                    files=files, projid=projid, curr_project=project_info, comment=project_db[projid]['comment'],
                    addfiles=(self.get_argument('uploadfiles', None) is not None))
