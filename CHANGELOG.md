# Data Delivery System Web / API: Changelog

Please add a _short_ line describing the PR you make, if the PR implements a specific feature or functionality, or refactor. Not needed if you add very small and unnoticable changes. Not needed when PR includes _only_ tests for already existing feature.

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
- Cronjob: Scheduled task for deleting unanswered invites after a week ([#1147](https://github.com/ScilifelabDataCentre/dds_web/pull/1147))
- Checkbox in registration form and policy to agree to ([#1151](https://github.com/ScilifelabDataCentre/dds_web/pull/1151))
- Patch: Add checks for valid public_id when creating new unit to avoid bucket name errors ([#1154](https://github.com/ScilifelabDataCentre/dds_web/pull/1154))

## Sprint (2022-04-20 - 2022-05-04)

- Renamed `api/units.py` to `api/superadmin_only.py` to reflect that it's only Super Admin accessible resources ([#1159](https://github.com/ScilifelabDataCentre/dds_web/pull/1159))
- Add unit tests for the "set_available_to_expired" and "set_expired_to_archived" functions ([#1158](https://github.com/ScilifelabDataCentre/dds_web/pull/1158))
- DC Branding: SciLifeLab logo + "Data Delivery System" in nav bar & DC branding in footer ([#1160](https://github.com/ScilifelabDataCentre/dds_web/pull/1160))

## Sprint (2022-05-04 - 2022-05-18)

- `adr-tools` to document architecture decisions ([#1161](https://github.com/ScilifelabDataCentre/dds_web/pull/1161))
- Bug: API returning float again and CLI `--size` flag works again ([#1162](https://github.com/ScilifelabDataCentre/dds_web/pull/1162))
- Bug: Check for timestamp `0000-00-00 00:00:00` added and invite deleted ([#1163](https://github.com/ScilifelabDataCentre/dds_web/pull/1163))
- Add documentation of status codes in `api/project.py` ([#1164](https://github.com/ScilifelabDataCentre/dds_web/pull/1164))
- Add ability to switch to using TOTP and back to HOTP for MFA ([#936](https://github.com/scilifelabdatacentre/dds_web/issues/936))
- Patch: Fix the warning in web for too soon TOTP login (within 90 seconds) ([#1173](https://github.com/ScilifelabDataCentre/dds_web/pull/1173))
- Bug: Do not remove the bucket when emptying the project ([#1172](https://github.com/ScilifelabDataCentre/dds_web/pull/1172))
- New `add-missing-buckets` argument option to the `lost-files` flask command ([#1174](https://github.com/ScilifelabDataCentre/dds_web/pull/1174))
- Bug: Corrected `lost-files` logic and message ([#1176](https://github.com/ScilifelabDataCentre/dds_web/pull/1176))

## Sprint (2022-05-18 - 2022-06-01)

- Allow all characters but unicode (e.g. emojis) in project description ([#1178](https://github.com/ScilifelabDataCentre/dds_web/pull/1178))
- Cronjob: Scheduled task for monthly usage data ([#1181](https://github.com/ScilifelabDataCentre/dds_web/pull/1181))
- New tests for `dds_web/__init__.py` ([#1185](https://github.com/ScilifelabDataCentre/dds_web/pull/1185))
- New tests for `dds_web/utils.py` ([#1188](https://github.com/ScilifelabDataCentre/dds_web/pull/1188))
- Removed FontAwesome from web ([#1192](https://github.com/ScilifelabDataCentre/dds_web/pull/1192))

## Sprint (2022-06-01 - 2022-06-15)

- Change FontAwesome source link to own license ([#1194](https://github.com/ScilifelabDataCentre/dds_web/pull/1194))
- Display MOTD on web ([#1196](https://github.com/ScilifelabDataCentre/dds_web/pull/1196))

## Sprint (2022-06-15 - 2022-06-29)

- Get MOTD from API ([#1198](https://github.com/ScilifelabDataCentre/dds_web/pull/1198))
- New endpoint for listing all users ([#1204](https://github.com/ScilifelabDataCentre/dds_web/pull/1204))
- Only print warning about missing bucket if the project is active ([#1203](https://github.com/ScilifelabDataCentre/dds_web/pull/1203))
- Removed version check ([#1206](https://github.com/ScilifelabDataCentre/dds_web/pull/1206))

## Summer 2022

- Do not send one time code to email if the email 2fa is getting activated ([#1236](https://github.com/ScilifelabDataCentre/dds_web/pull/1236))
- Raise AccessDeniedError with message when token specified but user not existent ([#1235](https://github.com/ScilifelabDataCentre/dds_web/pull/1235))
- Display multiple MOTDS ([#1212](https://github.com/ScilifelabDataCentre/dds_web/pull/1212))

## Sprint (2022-08-18 - 2022-09-02)

- Allow Super Admins to deactivate user 2FA via authenticator app ([#1247](https://github.com/ScilifelabDataCentre/dds_web/pull/1247))
- Get troubleshooting document from Confluence ([#1244](https://github.com/ScilifelabDataCentre/dds_web/pull/1244))
- Quarterly cron job calculating projects storage usage based on the database ([#1246](https://github.com/ScilifelabDataCentre/dds_web/pull/1246))
- Add Technical Overview page with links to Confluence and to a PDF download ([#1250](https://github.com/ScilifelabDataCentre/dds_web/pull/1250))
- Technical Overview moved to repository ([#1250](https://github.com/ScilifelabDataCentre/dds_web/pull/1253))
- Troubleshooting document moved to repository and buttons added to web to link and download ([#1255](https://github.com/ScilifelabDataCentre/dds_web/pull/1255))

## Sprint (2022-09-02 - 2022-09-16)

- Add storage usage information in the Units listing table for Super Admin ([#1264](https://github.com/ScilifelabDataCentre/dds_web/pull/1264))
- New endpoint for setting project as busy / not busy ([#1266](https://github.com/ScilifelabDataCentre/dds_web/pull/1266))
- Check for if project busy before status change ([#1266](https://github.com/ScilifelabDataCentre/dds_web/pull/1266))
- Bug fix: Default timestamps fixed ([#1271](https://github.com/ScilifelabDataCentre/dds_web/pull/1271))
- Change docker image to alpine ([#1272](https://github.com/ScilifelabDataCentre/dds_web/pull/1272))
- Added trivy when publishing to dockerhub ([#1276](https://github.com/ScilifelabDataCentre/dds_web/pull/1276))
- Bug fix: Cost value displayed by the --usage flag fixed ([#1274](https://github.com/ScilifelabDataCentre/dds_web/pull/1274))

## Sprint (2022-09-16 - 2022-09-30)

- New endpoint: SendMOTD - send important information to users ([#1283](https://github.com/ScilifelabDataCentre/dds_web/pull/1283))
- New table: `Maintenance`, for keeping track of DDS maintenance mode ([#1284](https://github.com/ScilifelabDataCentre/dds_web/pull/1284))
- New endpoint: SetMaintenance - set maintenance mode to on or off ([#1286](https://github.com/ScilifelabDataCentre/dds_web/pull/1286))
- New endpoint: AnyProjectsBusy - check if any projects are busy in DDS ([#1288](https://github.com/ScilifelabDataCentre/dds_web/pull/1288))

## Sprint (2022-09-30 - 2022-10-14)

- Bug fix: Fix the Invite.projects database model ([#1290](https://github.com/ScilifelabDataCentre/dds_web/pull/1290))
- New endpoint: ListInvites - list invites ([#1294](https://github.com/ScilifelabDataCentre/dds_web/pull/1294))

## Sprint (2022-10-14 - 2022-10-28)

- Limit projects listing to active projects only; a `--show-all` flag can be used for listing all projects, active and inactive ([#1302](https://github.com/ScilifelabDataCentre/dds_web/pull/1302))
- Return name of project creator from UserProjects ([#1303](https://github.com/ScilifelabDataCentre/dds_web/pull/1303))
- Add version to the footer of the web pages ([#1304](https://github.com/ScilifelabDataCentre/dds_web/pull/1304))
- Add link to the dds instance to the end of all emails ([#1305](https://github.com/ScilifelabDataCentre/dds_web/pull/1305))
- Troubleshooting steps added to web page ([#1309](https://github.com/ScilifelabDataCentre/dds_web/pull/1309))
- Bug: Return instead of project creator if user has been deleted ([#1311](https://github.com/ScilifelabDataCentre/dds_web/pull/1311))
- New endpoint: ProjectInfo - display project information ([#1310](https://github.com/ScilifelabDataCentre/dds_web/pull/1310))

## Sprint (2022-11-11 - 2022-11-25)

- Link to "How do I get my user account?" from the login form ([#1318](https://github.com/ScilifelabDataCentre/dds_web/pull/1318))

## Sprint (2022-11-25 - 2022-12-09)

- Changed support email ([#1324](https://github.com/ScilifelabDataCentre/dds_web/pull/1324))
- Allow Super Admin login during maintenance ([#1333](https://github.com/ScilifelabDataCentre/dds_web/pull/1333))

## Sprint (2022-12-09 - 2023-01-09) - Longer sprint due to Christmas

- Dependency: Bump `certifi` due to CVE-2022-23491 ([#1337](https://github.com/ScilifelabDataCentre/dds_web/pull/1337))
- Dependency: Bump `jwcrypto` due to CVE-2022-3102 ([#1339](https://github.com/ScilifelabDataCentre/dds_web/pull/1339))
- Cronjob: Get number of units and users for reporting ([#1324](https://github.com/ScilifelabDataCentre/dds_web/pull/1335))
- Add ability to change project information via ProjectInfo endpoint ([#1331](https://github.com/ScilifelabDataCentre/dds_web/pull/1331))
- Fix the reporting file path ([1345](https://github.com/ScilifelabDataCentre/dds_web/pull/1345))

## Sprint (2023-01-09 - 2023-01-20)

- Refactoring: Move flask commands to own module `commands.py` ([#1351](https://github.com/ScilifelabDataCentre/dds_web/pull/1351))
