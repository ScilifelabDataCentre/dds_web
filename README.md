![CodeQL](https://github.com/ScilifelabDataCentre/dds_web/actions/workflows/codeql-analysis.yml/badge.svg)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
![Linting](https://github.com/ScilifelabDataCentre/dds_web/actions/workflows/python-black.yml/badge.svg)
![Tests](https://github.com/ScilifelabDataCentre/dds_web/actions/workflows/docker-compose-tests.yml/badge.svg)
[![codecov](https://codecov.io/gh/ScilifelabDataCentre/dds_web/branch/dev/graph/badge.svg?token=r5tM6o08Sd)](https://codecov.io/gh/ScilifelabDataCentre/dds_web)

# SciLifeLab Data Centre - Data Delivery System

**A single cloud-based system for all SciLifeLab units, where data generated throughout each project can be delivered to the research groups in a fast, secure and simple way.**

> _This project is supported by EIT Digital, activity number 19390. This deliverable consists of design document and implementation report of application and validation of VEIL.AI technology in SciLifeLab context in Sweden._

The Delivery Portal consists of two components:

- The _backend api_ handling the requests and the logic behind the scenes.
  - <https://github.com/ScilifelabDataCentre/dds_web> (this repository)
- The _command line interface (CLI)_. This will be used for data delivery within larger projects
  and/or projects resulting in the production of large amounts of data, e.g. sequence data.
  - <https://github.com/ScilifelabDataCentre/dds_cli>

The backend interface is built using [Flask](https://flask.palletsprojects.com/en/2.0.x/).

See the [ADR](https://github.com/ScilifelabDataCentre/dds_web/wiki/Architecture-Decision-Record,-ADR) for information on the design decisions.

---

## Development

### Running with Docker

When developing this software, we recommend that you run the web server locally using Docker.
You can download Docker here: <https://docs.docker.com/get-docker/>

Then, fork this repository and clone to your local system.
In the root folder of the repo, run the server as follows:

There are multiple profiles prepared depending on your needs:

```bash
docker-compose up
```

This command will orchestrate the building and running of two containers: one for the SQL database (`mariadb`) and one for the application.

```bash
docker-compose --profile dev up
```

This will give you the above two containers, but also `mailcatcher` that will allow you to read
any sent emails by going to `localhost:1080` in a web browser.

```bash
docker-compose --profile full-dev up
```

Will also activate minio for s3 storage (clearly not functional with cli) and redis to enable a persistent limiter for the API.
You also need to uncomment `RATELIMIT_STORAGE_URI` in `docker-compose.yml` to enable redis.

If you prefer, you can run the web servers in 'detached' mode with the `-d` flag, which does not block your terminal.
If using this method, you can stop the web server with the command `docker-compose down`.

### CLI development against local environment

```bash
docker-compose --profile cli up
```

Will start database, backend, minio, and mailcatcher. Will also start an extra container prepared for working with the CLI.

Requires that dds_cli is checked out in `../dds_cli` (otherwise adapt the volume path in `docker-compose.yml`).

1. Start docker-compose with the `cli` profile
2. Inject into the `dds_cli` container:

   ```bash
   docker exec -it dds_cli /bin/bash
   ```

Then you can freely use the dds cli component against the local development setup in the active CLI.

### Python debugger inside docker

It's possible to use the interactive debugging tool `pdb` inside Docker with this method:

1. Edit the `docker-compose.yml` and for the `backend` service, add:

   ```yaml
   tty: true
   stdin_open: true
   ```

   just under

   ```yaml
   ports:
     - 127.0.0.1:5000:5000
   ```

2. Put `import pdb; pdb.set_trace()` in the python code where you would like to activate the debugger.
3. Run with docker-compose as normal.
4. Find out the id of the container running the `backend`.

   ```bash
   docker container ls
   ```

5. Attach to the running backend container:

   ```bash
   docker container attach <container_id/name>
   ```

### Config settings

When run from the cloned repo, all settings are set to default values.
These values are publicly visible on GitHub and **should not be used in production!**

> ❗️
> **At the time of writing, upload within projects created in the development database will most likely not work.**
> To use the upload functionality with the `CLI`, first create a project.

The following test usernames ship in the development setup:

- `superadmin`
- `unituser_1`
- `unituser_2`
- `researchuser_1`
- `researchuser_2`

All have the password: `password`

### Database changes

If you modify the database models (e.g. tables or indexes), you must create a migration for the changes. We use `Alembic` (via `flask-migrate`) which compares our database models with the running database to generate a suggested migration.

The new migration can be autogenerated in two main ways:

1. Make sure the development setup is running (`docker-compose up`) while doing the changes.

2. Reset the container using `docker-compose down` and then remove `flask init-db $$DB_TYPE &&` in `docker-compose.yml`. It will prevent the population of the database, allowing you to install the old schema and build your migration on top of it by running `docker-compose up`

To create the migration, run the command `flask db migrate -m <migration name>` in the running backend:

```bash
docker exec dds_backend flask db migrate -m <migration name>
```

This will create a migration in the folder `migrations/versions`. Confirm that the changes in the file match the changes you did, otherwise change the `upgrade` and `downgrade` functions as needed. Keep an eye out for changes to the `apscheduler` tables and indexes, and make sure they are not included in the migration. Once the migration looks ok, test it by running `flask db upgrade` in the backend:

```bash
docker exec dds_backend flask db upgrade
```

Finally, confirm that the database looks correct after running the migration and commit the migration file to git. Note that you need to run `black` on the generated migration file.

> ↩️ If you want to start over, restore the content of `migrations/versions` (remove new files, run `git restore` on the folder) and start from autogeneration method 2.

### Database issues while running `docker-compose up`

If you run into issues with complaints about the db while running `docker-compose up` you can try to reset the containers by running `docker-compose down` before trying again. If you still have issues, try cleaning up containers and volumes manually.

> ⚠️ These commands will remove _all_ containers and volumes!
> If you are working on other projects please be more selective.

```bash
docker rm $(docker ps -a -q) -f
docker volume prune
```

Then run `docker-compose up` as normal. The images will be rebuilt from scratch before launch.

If there are still issues, try deleting the `pycache` folders and repeat the above steps.

### Run tests

Tests run on github actions on every pull request and push against master and dev. To run the tests locally, use this command:

```bash
docker-compose -f docker-compose.yml -f tests/docker-compose-test.yml up --build --exit-code-from backend
```

This will create a test database in the mariadb container called `DeliverySystemTest` which will be populated before a test and emptied after a test has finished.

It's possible to supply arguments to pytest via the environment variable `$DDS_PYTEST_ARGS`.
For example to only run the `test_x` inside the file `tests/test_y.py` you would set this variable as follows: `export DDS_PYTEST_ARGS=tests/test_y.py::test_x`.

To run interactively, use the following command:

```bash
docker-compose -f docker-compose.yml -f tests/docker-compose-test-interactive.yml up --build --exit-code-from backend
```

Then in a new terminal, shell into the container and run pytest:

```bash
docker exec -it dds_backend /bin/bash
```

```bash
pytest
```

If you want to run tests quickly, without rebuilding the database each time, set the `SAVE_DB` environment variable:

```bash
SAVE_DB=1 pytest
```

Note that this stops the database from being deleted, so it will speed up the _next_ run.
Equally, if you want to tear down you need to run pytest _twice_ without it, as it only affects the tear down.

---

## Production

The production version of the backend image is published at [Dockerhub](https://hub.docker.com/repository/docker/scilifelabdatacentre/dds-backend). It can also be built by running:

```bash
docker build --target production -f Dockerfiles/backend.Dockerfile .
```

Use `docker-compose.yml` as a reference for the required environment.

### Configuration

The environment variable `DDS_APP_CONFIG` defines the location of the config file, e.g. `/code/dds_web/dds_app.cfg`. The config values are listed in `dds_web/config.py`. Add them to the file in the format:

```python
MAX_CONTENT_LENGTH = 0x1000000
MAX_DOWNLOAD_LIMIT = 1000000000
```

> ❗ It is recommended that you redefine all values in `config.py` in your config file to avoid using default values by mistake.

### Initialise the database

Before you can use the system, you must run `flask db upgrade` to initialise the database schema and prepare for future database migrations. You can also add a superuser by running `flask init-db production`. In order to customize the user, make sure to set the `SUPERADMIN*` config options.

### Upgrades

Whenever you upgrade to a newer version, start by running `flask db upgrade` to make sure that the database schema is up-to-date.
