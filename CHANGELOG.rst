Changelog
==========

.. _2.13.1:

2.13.1 - 2025-09-22
~~~~~~~~~~~~~~~~~~~~

- 🐛 Bug Fixes
    - Disable autoflush on project creation and assure no duplicate public ID
    - Fix bug: Users should be able to release once and extend twice
- 📄 Documentation
    - Correct key access swagger references 
- 🛡️ Dependencies
    - Bump node packages using `npm audit fix`
    - Bump python packages to solve vulnerabilities:
        - `cryptography` from 42.0.4 to 44.0.1
        - `dnspython` from 2.2.0 to 2.6.1
        - `idna` from 3.3 to 3.7
        - `Pillow` from 10.2.0 to 10.3.0
        - `requests` from 2.32.0 to 2.32.4

.. _2.13.0:

2.13.0 - 2025-08-25
~~~~~~~~~~~~~~~~~~~~

- 🚀 Features
    - Set project Deletion as a background task

.. _2.12.0:

2.12.0 - 2025-08-06
~~~~~~~~~~~~~~~~~~~~

- 🚀 Features
    - Set project archivation as a background task

- 🐛 Bug Fixes
    - Fix bug: Users should be able to release the project once and extend / rerelease the project twice

- 🛡️ Dependencies
    - Bump werkzeug from 3.0.3 to 3.0.6

.. _2.11.0:

2.11.0 - 2025-06-05
~~~~~~~~~~~~~~~~~~~~

- 🚀 Features
    - Change RQ worker config to keep one worker per pod and increase default timeout
    - Enqueue Message Of the Day

- 🐛 Bug Fixes

    - Move project inactivation to after data-removal in order to ensure projects cannot be inactive while still containing data (#1605)

- 🛡️ Dependencies

    - Bump jinja2 from 3.1.3 to 3.1.6 (#1606)

.. _2.10.0:

2.10.0 - 2025-04-08
~~~~~~~~~~~~~~~~~~~~

- 🚀 Features
    - Implement Redis Queue for Async Requests & Project Deletion

.. _2.9.0:

2.9.0 - 2024-12-18
~~~~~~~~~~~~~~~~~~

- New features:
    - Delivery directory names now include 'Upload' or 'Download' for clarity.
    - Monitor usage now sends warnings to the affected unit and Data Centre when approaching the allocated quota.
- Bugs fixed:
    - Improved error message for downloads after a password reset.
    - Fixed the dds ls --tree command.
    - Pinned mariadb-client version in backend Dockerfile for stability.
    - Resolved Node.js vulnerabilities with npm audit fix.
- Logging:
    - Removed invalid token exceptions from logs.
    - Logged usernames for password resets.
    - Filtered out MaintenanceModeException from logs.

.. _2.8.1:

2.8.1 - 2024-10-23
~~~~~~~~~~~~~~~~~~~~~~~

- New features:
    - warning_level option when a unit is created defaults to 0.8.
    - Add option to MOTD endpoint to send an email to unit users only.
    - Modify the invoicing commands to send the instance name in the emails.
- Documentation: Update readme to indicate that the backend image is published to GGCR, not DockerHub.

.. _2.8.0:

2.8.0 - 2024-09-24
~~~~~~~~~~~~~~~~~~~~~~~

- New features:
    - Technical Overview and Troubleshooting updated and made available as pdf.
    - Added Flask command for updating units quota.
- Dependencies:
    - `certifi` from `2023.07.22` to `2024.7.4`
    - `requests` from `2.31.0` to `2.32.0`
    - `wrapt` from `1.13.3` to `1.14.0`
- Dependencies (tests):
    - `pyfakefs` from `4.5.5` to `5.3.0`
- Update base image for the docker containers from `python:3.11-alpine` to `python:3.12-alpine`

.. _2.7.1:

2.7.1 - 2024-06-26
~~~~~~~~~~~~~~~~~~~~~~~

- New features:
    - Fix the Project endpoint according to OpenAPI standard.
    - Fix the Superadmin endpoint according to OpenAPI standard.
- Dependencies: 
    - `Authlib` from `0.15.5` to `1.3.1`
    - `PyMySQL` from `1.0.2` to `1.1.1`
- Node modules: 
    - `braces` from `3.0.2` to `3.0.3`
    - `fill-range` from `7.0.1` to `7.1.1`
    - `ip` from `2.0.0` to `9.0.5`
    - `socks` from `2.7.1` to `2.8.3`
    - `tar` from `6.1.15` to `6.2.1`

.. _2.7.0:

2.7.0 - 2024-05-29
~~~~~~~~~~~~~~~~~~~~~~~

- New features:
    - Fix the User endpoint according to OpenAPI standard.
    - Added email contact to troubleshooting page
- Dependencies: 
    - `Werkzeug` from `2.2.3` to `3.0.3`
    - `Flask-WTF` from `1.0.0` to `1.1.2`
    - `Flask-Login` from `0.6.2` to `0.6.3`
    - `Flask-HTTPAuth` from `4.5.0` to `4.8.0`
- Bugs fixed:
    - Boolean inputs in requests are parsed with flask types.


.. _2.6.4:

2.6.4 - 2023-04-10
~~~~~~~~~~~~~~~~~~~~~~~

- New features:
    - Fix the files endpoint acording to openAPI standar .
    - Added email contact to troubleshouting page
- Dependencies: 
    - `jwcrypto` from `1.5.1` to `1.5.6`
- Update base image for the docker containers from `python:3.10-alpine` to `python:3.11-alpine`

.. _2.6.3:

2.6.3 - 2023-02-27
~~~~~~~~~~~~~~~~~~~~~~~

- New features:
    - User Agreement is available to read during registration, as well as always accesible through the footer of the webpage .
- Dependencies: 
    - `Criptography` from `41.0.6` to `42.0.4`

.. _2.6.2:

2.6.2 - 2023-02-13
~~~~~~~~~~~~~~~~~~~~~~~

- New features:
    - Documentation is now available at `https://delivery.scilifelab.se/documentation/`. Some endpoints do not comply with the openAPI standards and are not properly documented.
- Dependencies: 
    - `jinja2` from `3.0.3` to `3.1.3`
    - `jwcrypto` from `1.4.2` to `1.5.1`
    - `Pillow` from `10.1.0` to `10.2.0`


.. _2.6.1:

2.6.1 - 2023-12-20
~~~~~~~~~~~~~~~~~~~~~~~

- Bugs fixed:
    - Listing users invites will now show if the invite is for Project Owner.
    - Permissions issue for `send-usage` command in testing and production environment.
- Dependencies: 
    - `Cryptography` from `41.0.3` to `41.0.6`

.. _2.6.0:

2.6.0 - 2023-11-22
~~~~~~~~~~~~~~~~~~~~~~~

- New endpoint `AddFailedFiles` to allow a retry of saving files to the database after issues during upload.
- Cronjobs:
    - Updated command: `quarterly-usage` changed to `monthly-usage` and refactored to catch errors and send emails.
    - New command `send-usage` to collect usage rows from the `Usage` table and send csv files to support email.
- Dependencies: 
    - `Pillow` from `9.3.0` to `10.1.0`
    - `urllib3` from `1.26.8` to `1.26.18`
    - `postcss` (npm) from `8.4.28` to `8.4.31`

.. _2.5.2:

2.5.2 - 2023-10-25
~~~~~~~~~~~~~~~~~~~~~

- Users can revoke project access given to unaccepted invites (e.g. after a mistake).
- Email layout changed. When project is released, important information is now highlighted, and the Project Title is displayed along with the DDS project ID.
- New endpoint `ProjectStatus.patch`: Unit Admins / Personnel can extend the project deadline.

.. _2.5.1:

2.5.1 - 2023-09-27
~~~~~~~~~~~~~~~~~~~

- Super Admins only: 
    - New endpoint `MaintenanceMode.get`: Super Admins can get info on whether or not the DDS maintenance mode is on or off.
    - Statistics endpoint returns date of generated statistics, not time.  
- Bugs fixed:
    - Errors when attempting to create a project after it has failed due to a database error should now not happen; Database rollback added to project creation endpoint.
    - Researchers should now always appear in the list of project users after running `dds project access fix --project <proj_id>`; Missing database update added.
    - Expired invites are deleted automatically when invite is sent to user again; Deleting invite with `dds user delete --is-invite` is no longer necessary prior to a new `dds user add`. 
- Dependencies:
    - `MariaDB` from EOL `10.7.8` to LTS `10.11.5`

.. _2.5.0:

2.5.0 - 2023-08-30
~~~~~~~~~~~~~~~~~~~~~~~~

- Dependencies: 
    - `cryptography` from `39.0.1` to `41.0.3`
    - `certifi` from `2022.12.07` to `2023.07.22`
- _New_ project buckets will be created at a new storage location if Unit information has been updated with storage keys and information.
- Bug fixed: Listing projects via web interface works again
- Endpoint `ProjectBusy` is no longer usable; `dds-cli` versions prior to `2.2.0` will no longer work
- New endpoint `UnitUserEmails`: Super Admins can get primary emails for Unit Admins- and Personnel. This is for emailing purposes.
- Message about project being busy has been changed to a more accurate and understandable statement
- Documentation: Typo fixed in Technical Overview

.. _2.4.0:

2.4.0 - 2023-07-05
~~~~~~~~~~~~~~~~~~~

- Dependencies:
    - `requests` from `2.27.1` to `2.31.0`
    - `redis` from `4.4.4` to `4.5.5`
    - `Flask` from `2.0.3` to `2.2.5`
- Statistics:
    - Number of TBHours stored in the last month calculated and stored in DB
    - Number of TBHours stored since start calculated and stored in DB
    - Endpoint `Statistics` to return rows stored in the Reporting table 
- Full name of Unit Admins-, Personnel and Super Admins not shown to Researchers; Only display Unit name when...
    - Listing projects
    - Sending invites
    - Releasing projects
- Backend Flask command `lost-files` changed to group command with subcommands `ls`, `delete`, `add-missing-bucket`
 
.. _2.3.0: 

2.3.0 - 2023-06-07
~~~~~~~~~~~~~~~~~~~

- Changed the reporting command (cronjob) and added statistics calculations: 
    - Number of users in total and in different roles
    - Number of projects: Total, active and non-active
    - Amount of data (in TBs) currently stored and uploaded since start

.. _2.2.62:

2.2.62 - 2023-03-20
~~~~~~~~~~~~~~~~~~~~

- Added this version changelog. 
- Fixed bugs:
    - Percentage calculation in cronjob for monitoring unit usage has been fixed; Warning email will be sent to Data Centre when a units data usage on DDS reaches 80% of their allocated quota.
    - User is redirected to same page and message when attempting to reset their password, independent on if the email is registered to an active user or not.
    - Non-latin1 encodable characters are not allowed in passwords.
- The _default_ settings for the Argon2 password hashing function have been changed to increase the complexity and security.

.. _earlier-versions:

Earlier versions
~~~~~~~~~~~~~~~~~

Please see `the release page on GitHub <https://github.com/ScilifelabDataCentre/dds_web/releases>`_ for detailed information about the changes in each release.
