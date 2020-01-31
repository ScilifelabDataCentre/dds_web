#!/usr/bin/env python3
"""project.py"""


# IMPORTS ############################################################ IMPORTS #

from __future__ import absolute_import
import base
from base import BaseHandler

from dp_exceptions import DeliveryPortalException, CouchDBException

# GLOBAL VARIABLES ########################################## GLOBAL VARIABLES #


# CLASSES ############################################################ CLASSES #

class ProjectStatus(BaseHandler):
    """Handles change of project status (finished or ongoing)"""

    def post(self, projid):
        """Called by 'Mark project as finished' or 'Mark project as open'"""

        # If one of the buttons are pressed, open connection to database
        if ((self.get_argument('setasfinished', None) is not None)
                or (self.get_argument('setasopen', None) is not None)):
            project_db = self.couch_connect()['project_db']
            curr_proj = project_db[projid]  # The current project

            # If the 'Mark project as finished' button is pressed
            # Change status to 'Finished'
            # If the 'Mark project as open' button is pressed
            # Change status to 'Ongoing'
            if self.get_argument('setasfinished', None) is not None:
                curr_proj['project_info']['status'] = "Finished"
            elif self.get_argument('setasopen', None) is not None:
                curr_proj['project_info']['status'] = "Ongoing"

            try:
                project_db.save(curr_proj)  # Save changes
            except CouchDBException as cdbe:
                print(f"The project could not be saved: {cdbe}")
            else:
                try: 
                    self.render('project_page.html',
                                curr_user=self.current_user,
                                files=curr_proj['files'],
                                projid=projid,
                                curr_project=curr_proj['project_info'],
                                comment=curr_proj['commment'],
                                addfiles=(self.get_argument('uploadfiles', None) is not None))
                except DeliveryPortalException as dpe: 
                    print(f"The project page could not be rendered: {dpe}")


class ProjectHandler(BaseHandler):
    """Called by "See project" button.
    Connects to database and collects all files
    associated with the project and user. Renders project page."""

    def get(self, projid):
        """Renders the project page with projects and associated files."""

        try: 
            project_db = self.couch_connect()['project_db'][projid]
        except CouchDBException as cdbe:
            print(f"Project ID {projid} not in database: {cdbe}")
        else:
            # Save project files in dict
            files = {}
            if 'files' in project_db:
                files = project_db['files']

            try:
                self.render('project_page.html',
                            curr_user=self.current_user,
                            is_facility=(self.couch_connect()['user_db'][self.current_user]['role']=="facility"),
                            files=files, 
                            projid=projid,
                            curr_project=project_db['project_info'],
                            comment=project_db['comment'],
                            addfiles=(self.get_argument('uploadfiles', None) is not None))
            except DeliveryPortalException as dpe:
                print(f"The project page could not be rendered! {dpe}")


Datan som ni delar med er av ska användas för att testa delen med anonymiseringsverktyget. 