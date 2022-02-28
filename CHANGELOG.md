# Data Delivery System Web / API: Changelog

Please add a _short_ line describing the PR you make, if the PR implements a specific feature or functionality, or refactor. Not needed if you add very small and unnoticable changes.

## Sprint (2022-02-09 - 2022-02-23)
* Secure operations that require cryptographic keys are protected for each user with the user's password ([#889](https://github.com/ScilifelabDataCentre/dds_web/pull/889))
* Implemented the functionality to add project to the invites of a new user as outlined in [issue 887](https://github.com/scilifelabdatacentre/dds_web/issues/887) ([PR888](https://github.com/ScilifelabDataCentre/dds_web/pull/888)).
* Create endpoint for renewing users project access, e.g. after password reset ([886](https://github.com/ScilifelabDataCentre/dds_web/pull/885))
* Added tests for web login and change password ([900](https://github.com/ScilifelabDataCentre/dds_web/pull/900))
* Size-based log rotation working (15*1MiB)[#897](https://github.com/ScilifelabDataCentre/dds_web/pull/897))
* Added check for project status in RemoveContents endpoint as outlined in [issue 898](https://github.com/ScilifelabDataCentre/dds_web/issues/898) ([PR899](https://github.com/ScilifelabDataCentre/dds_web/pull/899)).
* Implemented the functionality to add project to the invites of a new user as outlined in [issue 887](https://github.com/scilifelabdatacentre/dds_web/issues/887) ([PR888](https://github.com/ScilifelabDataCentre/dds_web/pull/888)).
* Changed and fixed the implementation of password reset ([#891](https://github.com/ScilifelabDataCentre/dds_web/pull/891)
* Changed log rotation to standard format and set maximum to 1MiB per file, max 15 files ([897](https://github.com/ScilifelabDataCentre/dds_web/pull/897))
* Add functionality for reactivating project access for user ([886](https://github.com/ScilifelabDataCentre/dds_web/pull/886))
* Check if user is active before allowing password reset ([903](https://github.com/ScilifelabDataCentre/dds_web/pull/903))
* Add support for database migrations using flask-migrate/Alembic ([#890](https://github.com/ScilifelabDataCentre/dds_web/pull/890))
* Invite Researchers to projects ([911](https://github.com/ScilifelabDataCentre/dds_web/pull/911))
* Changed `is_sensitive` to `non_sensitive` and set to default False ([#913](https://github.com/ScilifelabDataCentre/dds_web/pull/913))
* Rearrangement and clean up of the token ([910](https://github.com/ScilifelabDataCentre/dds_web/pull/910))

## Sprint (2022-02-23 - 2022-03-09)
* Add landing page after password reset ([#931](https://github.com/ScilifelabDataCentre/dds_web/pull/931))
* Add endpoint for health check (intended for readinessProbe)  ([#933](https://github.com/ScilifelabDataCentre/dds_web/pull/933))
* Introduced a `--no-mail` flag in the CLI respectively a `send_email: True/False` json parameter to fix [#924](https://github.com/scilifelabdatacentre/dds_web/issues/924) ([#926](https://github.com/ScilifelabDataCentre/dds_web/pull/926))
* Invite Unit Admin (temporary way) ([#938](https://github.com/ScilifelabDataCentre/dds_web/pull/938))
* Add support for getting IPs from X-Forwarded-For ([#952](https://github.com/ScilifelabDataCentre/dds_web/pull/952))
