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
        for file_ in files:
            filename = file_['filename']

            try:
                with open(filename, "wb") as out:
                    out.write(file_['body'])
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

# stream_request_body -- apply to RequestHandler subclasses to enable streaming body support
# HTTPServerRequest.body = undefined
# RequestHandler.get_argument --> body arguments not included
# RequestHandler.prepare =  called when the request headers have been read instead
#                           of after the entire body has been read
# data_received(self, data) =   called zero or more times as data is available.
#                               if request has empty body, not called
# prepare & data_received = may return Futures --> next method not called until
#                           those futures have been completed
# The regular HTTP method will be called after the entire body has been read
# @stream_request_body
# class UploadHandler(BaseHandler):
#     """docstring"""
#
#     # Hook for subclass initialization. Called for each request.
#     def initialize(self):
#         """docstring"""
#         self.bytes_read = 0
#         self.data = b''
#
#     # Called at the beginning of a request before get/post/etc.
#     def prepare(self):
#         self.request.connection.set_max_body_size(MAX_STREAMED_SIZE)
#         self.boundary = self.request.headers['Content-Type'].split('boundary=')[-1]
#
#     # Implement this method to handle streamed request data.
#     def data_received(self, chunk):
#         self.bytes_read += len(chunk)
#         self.data += chunk
#         with open('boundaryfile', 'w') as f:
#             f.write(f"{self.data} \t {self.boundary} \n")
#
#     def post(self, projid):
#         """docstring"""
#         this_request = self.request
#         with open('file', 'w') as f:
#             f.write(f"{self.boundary} \n")
