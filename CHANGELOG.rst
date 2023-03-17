Changelog
==========

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