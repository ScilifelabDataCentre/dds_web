#!/usr/bin/env python3


# IMPORTS ############################################################ IMPORTS #
import logging

import base64
import tornado.autoreload
import tornado.ioloop
import tornado.gen
import tornado.web
import uuid
import pymysql
import tornado_mysql
import couchdb
import re

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

from utils.config import parse_config
config = parse_config()
site_base_url = f'{config["site_base_url"]}:{config["site_port"]}'

from tornado.options import define, options
define("port", default=config['site_port'], help="run on the given port", type=int)


# CLASSES ############################################################ CLASSES #
class ApplicationDP(tornado.web.Application):
    """docstring for ApplicationDP."""

    def __init__(self):
        """"""
        url = tornado.web.url
        handlers = [ url(r"/", MainHandler, name='home'),
                     url(r"/login", LoginHandler, name='login'),
                     url(r"/create", CreateDeliveryHandler, name='create'),
                     url(r"/logout", LogoutHandler, name='logout'),
                     url(r"/project/(?P<projid>.*)", ProjectHandler, name='project'),
                     url(r"/profile", ProfileHandler, name='profile'),
                     url(r"/info", InfoHandler, name='info'),
                     url(r"/contact", ContactHandler, name="contact")
                     # url(r"/files/(?P<pid>.*)", FileHandler, name='files')
                     ]
        settings = {"xsrf_cookies":True,
                    #"cookie_secret":base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes),
                    "cookie_secret":config["cookie_secret"], #for dev purpose, shoulde be removed in the end
                    "template_path":"html_templates",
                    "static_path":"files"
                    }

        if config.get('development_mode'):
            settings['debug'] = True
            settings['develop'] = True
            logging.getLogger().setLevel(logging.DEBUG)

        tornado.web.Application.__init__(self, handlers, **settings)


class AESKey:
    """"""

    def __init__(self, bytes=32):
        """
        :param bytes:
        """

        self.key = get_random_bytes(bytes)   # Switch to better method? More randomness? os.urandom()?

    def encrypt(self, id, extn="", file=False):
        """
        :param data:
        :param file:        True if the data is a file.
        :return:
        """

        if file:
            with open("{}.txt".format(id), 'rb') as f:
                with open("encrypted_{}{}".format(id, extn), 'wb') as enc_f:
                    while True:
                        cipher = AES.new(self.key, AES.MODE_GCM)                # Create cipher
                        plaintext = f.read(61440)                               # Read 60 KiB
                        if not plaintext:                                       # Stop encryption if nothing to encrypt
                            break
                        ciphertext, tag = cipher.encrypt_and_digest(plaintext)  # Encrypt and extract tag
                        enc_f.write(cipher.nonce + tag + ciphertext)            # Save nonce, tag and ciphertext
            return "OK"
        else:
            cipher = AES.new(self.key, AES.MODE_GCM)                # Create cipher
            ciphertext, tag = cipher.encrypt_and_digest(id)
            return ciphertext, tag, cipher.nonce


    def decrypt(self, id, extn, file=False, iv=b'', tag=b''):
        """
        :param data:
        :param file:    True if data is a file.
        :return:
        """

        if file:
            with open('encrypted_downloaded_{}{}'.format(id, extn), 'rb') as enc_f:
                with open('decrypted_{}{}'.format(id, extn), 'wb') as dec_f:
                    while True:
                        nonce = enc_f.read(16)
                        mac = enc_f.read(16)
                        if not nonce and not mac:
                            break
                        cipher = AES.new(self.key, AES.MODE_GCM, nonce)
                        ciphertext = enc_f.read(61440)

                        plaintext = cipher.decrypt_and_verify(ciphertext, mac)
                        dec_f.write(plaintext)
            return "OK"
        else:
            cipher = AES.new(self.key, AES.MODE_GCM, iv)
            plaintext = cipher.decrypt_and_verify(id, tag)
            return plaintext


class BaseHandler(tornado.web.RequestHandler):
    """docstring for BaseHandler"""
    def get_current_user(self):
        """"""
        return self.get_secure_cookie("user")

    def couch_connect(self):
        """Connect to a couchdb interface."""
        couch = couchdb.Server(f'{config["couch_url"]}:{config["couch_port"]}')
        couch.login(config['couch_username'], config['couch_password'])
        return couch


class ContactHandler(BaseHandler):
    """"""

    def get(self):
        message = "This is the page where contact info is displayed. "
        self.render("contact_page.html", user=self.current_user, message=message)


class CreateDeliveryHandler(BaseHandler):
    """Called by create button on home page.
    Renders form for a new delivery. """

    def get(self):
        """Renders form for a new delivery."""
        self.render('create_delivery.html', user=self.current_user,
                    pid="dgu8y3488hdfs8dh88r3")

    #@tornado.web.authenticated
    # def post(self):
    #     """"""
    #     self.render('create_delivery.html')
    #


class InfoHandler(BaseHandler):
    """ """

    def get(self):
        message = "This is an information page about the dp."
        self.render("info_dp.html", user=self.current_user, message=message)

class LoginHandler(BaseHandler):
    """ Handles request to log in user. """

    def check_permission(self, username, password):
        """Called by post.
        Connects to database and checks if user exists."""

        couch = self.couch_connect()
        db = couch['dp_users']

        # Searches database for user with matching email and password
        for id in db:
            for part in db[id]['user']:
                if db[id]['user']['email'] == username and db[id]['user']['password'] == password:
                    return True, id

        return False, ""    # Returns false and "" if user not found

    def get(self):
        """"""
        try:
            errormessage = self.get_argument("error")
        except:
            errormessage = ""

    def post(self):
        """Called by login button.
        Gets inputs from form and checks user permissions."""

        # Get form input
        user_email = self.get_body_argument("user_email")
        password = self.get_body_argument("password")

        # Check if user exists
        auth, id = self.check_permission(user_email, password)

        # Sets current user if user exists
        if auth:
            self.set_secure_cookie("user", id, expires_days=0.1)
            # Redirects to homepage via mainhandler
            self.redirect(site_base_url + self.reverse_url('home'))
        else:
            self.clear_cookie("user")
            self.write("Login incorrect.")


class LogoutHandler(BaseHandler):
    """Called by logout button.
    Logs user out, and redirects to login page via main handler."""
    def get(self):
        """Clears cookies and redirects to login page."""

        self.clear_cookie("user")
        self.redirect(site_base_url + self.reverse_url('home'))


class MainHandler(BaseHandler):
    """Checks if user is logged in and redirects to home page."""

    def get(self):
        """Renders login page if not logged in, otherwise homepage."""

        if not self.current_user:
            self.render('index.html')
        else:
            # Get projects associated with user and send to home page
            # with user and project info
            projects, email, is_facility = self.get_user_projects()

            homepage=""
            if is_facility:
                homepage = "facility_home.html"
            else:
                homepage = "home.html"

            self.render(homepage, user=self.current_user, email=email,
                        projects=projects)

    def get_user_projects(self):
        """Connects to database and saves projects in dictionary."""
        user = tornado.escape.xhtml_escape(self.current_user)   # Current user

        couch = self.couch_connect()
        user_db = couch['dp_users']
        proj_db = couch['projects']

        projects = {}

        # Gets all projects for current user and save projects
        # and their associated information
        if 'projects' in user_db[user]:
            for proj in user_db[user]['projects']:
                projects[proj] = proj_db[proj]['project_info']

        return projects, user_db[user]['user']['email'], ("facility" in user_db[user]["user"])


class ProfileHandler(BaseHandler):
    """Profile page."""

    def get(self):
        message="This is the profile page where one can change password etc. "

        self.render('profile.html', user=self.current_user, message=message)


class ProjectHandler(BaseHandler):
    """Called by "See project" button.
    Connects to database and collects all files
    associated with the project and user. Renders project page."""

    def post(self, projid):
        """"""
        couch = self.couch_connect()

        proj_name = self.get_body_argument('prj_name')
        proj_category = self.get_body_argument('prj_ord_cat')
        proj_id = self.get_body_argument('prj_ord_id')
        proj_description = self.get_body_argument('prj_desc')

        pi_name = self.get_body_argument('prj_pi_name')
        pi_email = self.get_body_argument('prj_pi_email')


    def get(self, projid):
        """"""
        couch = self.couch_connect()
        proj_db = couch['projects']

        project_info = proj_db[projid]['project_info']

        files = {}
        if 'files' in proj_db[projid]:
            files = proj_db[projid]['files']

        self.render('project_page.html', user=self.current_user,
                    files=files, project=project_info)


@tornado.web.stream_request_body        # Allows for uploading of large files
class UploadHandler(BaseHandler):
    """Class. Handles the upload of the file."""

    def initialize(self):
        """
        Initialized the file upload.
        :return: ----
        """

        self.bytes_read = 0
        self.data = b''
        self.id = str(uuid.uuid4())    # Unique id -- Bucket name
        self.aes_key = AESKey()
        self.bucket = "s3://kMTZXkjLvM47TFn11zjhHJ8UlkT8PxrS"

    def prepare(self):
        """
        Sets the max streamed size.
        :return: ----
        """

        self.request.connection.set_max_body_size(MAX_STREAMED_SIZE)

    def data_received(self, chunk):
        """
        Received the data.
        :param chunk:   chunk of data
        :return:        ----
        """

        self.bytes_read += len(chunk)
        self.data += chunk

    def post(self):
        """
        Saves the uploaded data and checks that the file is identical to the uploaded file.
        :return: ---
        """

        # this_request gives HTTPServerRequest(protocol='', host='', method='', uri='', version='', remote_ip='')
        this_request = self.request
        value = self.data       # Not really useful, self.data could just be used directly

        # Save uploaded file
        with open(self.id + ".txt", 'wb') as f:
            f.write(value)

        # Get file name and extension from header
        header_cmd = subprocess.Popen(['sed', '2!d', self.id + ".txt"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        file_name_orig = header_cmd.communicate()[0].decode().split(";")[2].split('"')[1]
        file_extn = "." + file_name_orig.split(".")[-1]

        # Delete header and tail from file
        print("[*]  Removing header and tail from file...")
        remove_header = subprocess.Popen(["sed", "-i", ".bak", "1,4d;$d", self.id + ".txt"],
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE).wait()
        remove_tail = subprocess.Popen(["sed", "-i", ".bak", "$d", self.id + ".txt"],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE).wait()
        os.remove(self.id + ".txt.bak")
        print("[*]  Header and tail removed.")

        # Generate, print and compare checksums
        print("[*]  Generating hashes and checking integrity...")
        hash_upload = hash_file(self.id + ".txt")
        hash_orig = hash_file('/Users/inaod568/Downloads/{}'.format(file_name_orig))
        print("[*]  The files are identical: ", (hash_orig == hash_upload))

        if hash_orig == hash_upload:
            # Encrypt file
            print("[*]  Beginning encryption...")
            file = True
            file_encrypted = self.aes_key.encrypt(self.id, file_extn, file=file)
            print("[*]  Encryption completed.")

            if file==True and file_encrypted == "OK":
                try:
                    os.remove(self.id + ".txt")
                except IOError:
                    print(sys.exc_info())

                # Get size of original and encrypted file:
                print("[*]  Calculating overhead...")
                file_size_orig = os.path.getsize('/Users/inaod568/Downloads/{}'.format(file_name_orig))
                file_size_upload = os.path.getsize('encrypted_{}{}'.format(self.id, file_extn))
                print("Original file size: {} MB, \t "
                      "Encrypted file size: {} MB, \n "
                      "[*]  Overhead: {} %".format(round(file_size_orig / 1e6, 3),
                                                   round(file_size_upload / 1e6, 3),
                                                   round((file_size_upload - file_size_orig) / file_size_orig, 3)))

            # Create bucket if bucket doesn't exist
            buckets = subprocess.Popen([options.s3, "ls"], stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE).communicate()[0].decode().split("\n")
            bucket_exists = False
            for buck in buckets:
                if buck.split(" ")[-1] == self.bucket:
                    bucket_exists = True

            if not bucket_exists:
                create_bucket = subprocess.Popen([options.s3, "mb", self.bucket],
                                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE).wait()

            # Put uploaded file in bucket
            print("[*]  Uploading file to bucket...")
            file_to_bucket = subprocess.Popen(['{}'.format(options.s3),     # s3cmd directory
                                               'put',                       # put = upload file to bucket
                                               'encrypted_{}{}'.format(self.id, file_extn),      # file name
                                               self.bucket],
                                              stdout=subprocess.PIPE, stderr=subprocess.PIPE).wait()
            print("[*]  File upload completed: encrypted_{}{}".format(self.id, file_extn))

            try:
                os.remove('encrypted_{}{}'.format(self.id, file_extn))
            except IOError:
                print(sys.exc_info())

            print("[*]  Beginning download...")
            file_from_bucket = subprocess.Popen(['{}'.format(options.s3),
                                                 'get',
                                                 '{}/encrypted_{}{}'.format(self.bucket, self.id, file_extn),
                                                 'encrypted_downloaded_{}{}'.format(self.id, file_extn)]).communicate()
            print("[*]  Download completed: encrypted_downloaded_{}{}".format(self.id, file_extn))

            print("[*]  Beginning decryption...")
            file_decrypted = self.aes_key.decrypt(self.id, file_extn, file=True)
            print("[*]  Decryption completed. File name: decrypted_{}{}".format(self.id, file_extn))

            if file_decrypted == "OK":
                os.remove('encrypted_downloaded_{}{}'.format(self.id, file_extn))

                print("[*]  Generating hashes and verifying integrity...")
                hash_download = hash_file('decrypted_{}{}'.format(self.id, file_extn))
                if hash_upload == hash_download:
                    print("[*]  SUCCESS!")

        return self.write('<input onClick="history.back()" type="button" value="Back" />')





# FUNCTIONS ######################################################## FUNCTIONS #

# MAIN ################################################################## MAIN #
def main():
    """"""
    # test_db_connection()

    # For devel puprose watch page changes
    if config.get('development_mode'):
        tornado.autoreload.start()
        tornado.autoreload.watch("html_templates/index.html")
        tornado.autoreload.watch("html_templates/home.html")
        tornado.autoreload.watch("html_templates/project_page.html")
        tornado.autoreload.watch("html_templates/style.css")
        tornado.autoreload.watch("html_templates/profile.html")
        tornado.autoreload.watch("html_templates/info_dp.html")
        tornado.autoreload.watch("html_templates/contact_page.html")

    application = ApplicationDP()
    application.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
