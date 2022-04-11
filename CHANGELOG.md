# Data Delivery System Web / API: Changelog

Please add a _short_ line describing the PR you make, if the PR implements a specific feature or functionality, or refactor. Not needed if you add very small and unnoticable changes.

## Sprint (2022-02-09 - 2022-02-23)

- Secure operations that require cryptographic keys are protected for each user with the user's password ([#889](https://github.com/ScilifelabDataCentre/dds_web/pull/889))
- Implemented the functionality to add project to the invites of a new user as outlined in [issue 887](https://github.com/scilifelabdatacentre/dds_web/issues/887) ([PR888](https://github.com/ScilifelabDataCentre/dds_web/pull/888)).
- Create endpoint for renewing users project access, e.g. after password reset ([886](https://github.com/ScilifelabDataCentre/dds_web/pull/885))
- Added tests for web login and change password ([900](https://github.com/ScilifelabDataCentre/dds_web/pull/900))
- Size-based log rotation working (15\*1MiB)[#897](https://github.com/ScilifelabDataCentre/dds_web/pull/897))
- Added check for project status in RemoveContents endpoint as outlined in [issue 898](https://github.com/ScilifelabDataCentre/dds_web/issues/898) ([PR899](https://github.com/ScilifelabDataCentre/dds_web/pull/899)).
- Implemented the functionality to add project to the invites of a new user as outlined in [issue 887](https://github.com/scilifelabdatacentre/dds_web/issues/887) ([PR888](https://github.com/ScilifelabDataCentre/dds_web/pull/888)).
- Changed and fixed the implementation of password reset ([#891](https://github.com/ScilifelabDataCentre/dds_web/pull/891)
- Changed log rotation to standard format and set maximum to 1MiB per file, max 15 files ([897](https://github.com/ScilifelabDataCentre/dds_web/pull/897))
- Add functionality for reactivating project access for user ([886](https://github.com/ScilifelabDataCentre/dds_web/pull/886))
- Check if user is active before allowing password reset ([903](https://github.com/ScilifelabDataCentre/dds_web/pull/903))
- Add support for database migrations using flask-migrate/Alembic ([#890](https://github.com/ScilifelabDataCentre/dds_web/pull/890))
- Invite Researchers to projects ([911](https://github.com/ScilifelabDataCentre/dds_web/pull/911))
- Changed `is_sensitive` to `non_sensitive` and set to default False ([#913](https://github.com/ScilifelabDataCentre/dds_web/pull/913))
- Rearrangement and clean up of the token ([910](https://github.com/ScilifelabDataCentre/dds_web/pull/910))

## Sprint (2022-02-23 - 2022-03-09)

- Add landing page after password reset ([#931](https://github.com/ScilifelabDataCentre/dds_web/pull/931))
- Add endpoint for health check (intended for readinessProbe) ([#933](https://github.com/ScilifelabDataCentre/dds_web/pull/933))
- Introduced a `--no-mail` flag in the CLI respectively a `send_email: True/False` json parameter to fix [#924](https://github.com/scilifelabdatacentre/dds_web/issues/924) ([#926](https://github.com/ScilifelabDataCentre/dds_web/pull/926))
- Invite Unit Admin (temporary way) ([#938](https://github.com/ScilifelabDataCentre/dds_web/pull/938))
- Add support for getting IPs from X-Forwarded-For ([#952](https://github.com/ScilifelabDataCentre/dds_web/pull/952))
- Relax requirements for usernames (wider length range, `.` and `-`) ([#943](https://github.com/ScilifelabDataCentre/dds_web/pull/943))
- Delay committing project to db until after the bucket has been created ([#967](https://github.com/ScilifelabDataCentre/dds_web/pull/967))
- Fix logic for notification about sent email ([#963](https://github.com/ScilifelabDataCentre/dds_web/pull/963))
- Extended the `dds_web.api.dds_decorators.logging_bind_request` decorator to catch all not yet caught exceptions and make sure they will be logged ([#958](https://github.com/ScilifelabDataCentre/dds_web/pull/958)).
- Increase the security of the session cookie using HTTPONLY and SECURE ([#972](https://github.com/ScilifelabDataCentre/dds_web/pull/972))
- Add role when listing project users ([#974](https://github.com/ScilifelabDataCentre/dds_web/pull/974))
- Add custom error messages to registration form ([#975](https://github.com/ScilifelabDataCentre/dds_web/pull/975))
- Fix format of self deletion email ([#984](https://github.com/ScilifelabDataCentre/dds_web/pull/984))
- Add a full zero-conf development environment ([#993](https://github.com/ScilifelabDataCentre/dds_web/pull/993))
- Include frontend build in the backend production target ([#1011](https://github.com/ScilifelabDataCentre/dds_web/pull/1011))
- Correct response about project being created when email validation fails for users ([#1014](https://github.com/ScilifelabDataCentre/dds_web/pull/1014))
- Introduced an additional validator `dds_web.utils.contains_disallowed_characters` to fix issue [#1007](https://github.com/scilifelabdatacentre/dds_web/issues/1007) ([#1021](https://github.com/ScilifelabDataCentre/dds_web/pull/1021)).
- Fix regex for listing and deleting files [#1029](https://github.com/scilifelabdatacentre/dds_web/issues/1029)
- Hides the "Size" and "total_size" variables according to the role and project status ([#1032](https://github.com/ScilifelabDataCentre/dds_web/pull/1032)).

## Sprint (2022-03-09 - 2022-03-23)

- Introduce a separate error message if someone tried to add an unit user to projects individually. ([#1039](https://github.com/ScilifelabDataCentre/dds_web/pull/1039))
- Catch KeyNotFoundError when user tries to give access to a project they themselves do not have access to ([#1045](https://github.com/ScilifelabDataCentre/dds_web/pull/1045))
- Display an error message when the user makes too many authentication requests. ([#1034](https://github.com/ScilifelabDataCentre/dds_web/pull/1034))
- When listing the projects, return whether or not the user has a project key for that particular project ([#1049](https://github.com/ScilifelabDataCentre/dds_web/pull/1049))
- New endpoint for Unit Personnel and Admins to list the other Unit Personnel / Admins within their project ([#1050](https://github.com/ScilifelabDataCentre/dds_web/pull/1050))
- Make previous HOTP invalid at password reset ([#1054](https://github.com/ScilifelabDataCentre/dds_web/pull/1054))
- New PasswordReset table to keep track of when a user has requested a password reset ([#1058](https://github.com/ScilifelabDataCentre/dds_web/pull/1058))
- New endpoint for listing Units as Super Admin ([1060](https://github.com/ScilifelabDataCentre/dds_web/pull/1060))
- New endpoint for listing unit users as Super Admin ([#1059](https://github.com/ScilifelabDataCentre/dds_web/pull/1059))
- Future-proofing the migrations ([#1040](https://github.com/ScilifelabDataCentre/dds_web/pull/1040))
- Return int instead of string from files listing and only return usage info if right role ([#1070](https://github.com/ScilifelabDataCentre/dds_web/pull/1070))
- Batch deletion of files (breaking atomicity) ([#1067](https://github.com/ScilifelabDataCentre/dds_web/pull/1067))
- Change token expiration time to 7 days (168 hours) ([#1061](https://github.com/ScilifelabDataCentre/dds_web/pull/1061))
- Add possibility of deleting invites (temporary fix in delete user endpoint) ([#1075](https://github.com/ScilifelabDataCentre/dds_web/pull/1075))
- Flask command `create-unit` to create unit without having to interact with database directly ([#1075](https://github.com/ScilifelabDataCentre/dds_web/pull/1075))
- Let project description include . and , ([#1080](https://github.com/ScilifelabDataCentre/dds_web/pull/1080))
- Catch OperationalError if there is a database malfunction in `files.py` ([#1089](https://github.com/ScilifelabDataCentre/dds_web/pull/1089))
- Switched the validation for the principal investigator from string to email ([#1084](https://github.com/ScilifelabDataCentre/dds_web/pull/1084)).

## Sprint (2022-03-23 - 2022-04-06)

- Add link in navbar to the installation documentation ([#1112](https://github.com/ScilifelabDataCentre/dds_web/pull/1112))
- Change from apscheduler to flask-apscheduler - solves the app context issue ([#1109](https://github.com/ScilifelabDataCentre/dds_web/pull/1109))
- Send an email to all Unit Admins when a Unit Admin has reset their password ([#1110](https://github.com/ScilifelabDataCentre/dds_web/pull/1110)).
- Patch: Add check for unanswered invite when creating project and adding user who is already invited ([#1117](https://github.com/ScilifelabDataCentre/dds_web/pull/1117))
- Cronjob: Scheduled task for changing project status from Available to Expired ([#1116](https://github.com/ScilifelabDataCentre/dds_web/pull/1116))
- Cronjob: Scheduled task for changing project status from Expired to Archived ([#1115](https://github.com/ScilifelabDataCentre/dds_web/pull/1115))
- Add a Flask command for finding and deleting "lost files" (files that exist only in db or s3) ([#1124](https://github.com/ScilifelabDataCentre/dds_web/pull/1124))

## Sprint (2022-04-06 - 2022-04-20)

- New endpoint for adding a message of the day to the database ([#1136](https://github.com/ScilifelabDataCentre/dds_web/pull/1136))
- Patch: Custom error for PI email validation ([#1146](https://github.com/ScilifelabDataCentre/dds_web/pull/1146))
- New Data Delivery System logo ([#1148](https://github.com/ScilifelabDataCentre/dds_web/pull/1148))
