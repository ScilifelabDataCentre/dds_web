Changelog
==========

.. _2.3.1:

2.3.1 - 2023-07-05
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