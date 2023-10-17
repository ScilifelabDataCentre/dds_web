Changelog
==========

.. _2.5.2:

2.5.2 - 2023-10-25
~~~~~~~~~~~~~~~~~~~~~

- Users can revoke project access given to unaccepted invites (e.g. after a mistake).
- Email layout changed. When project is released, important information is now highlighted, and the Project Title is displayed along with the DDS project ID.

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
