![CodeQL](https://github.com/ScilifelabDataCentre/dds_web/actions/workflows/codeql-analysis.yml/badge.svg)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
![Linting](https://github.com/ScilifelabDataCentre/dds_web/actions/workflows/python-black.yml/badge.svg)
![Tests](https://github.com/ScilifelabDataCentre/dds_web/actions/workflows/docker-compose-tests.yml/badge.svg)
[![codecov](https://codecov.io/gh/ScilifelabDataCentre/dds_web/branch/dev/graph/badge.svg?token=r5tM6o08Sd)](https://codecov.io/gh/ScilifelabDataCentre/dds_web)

# SciLifeLab Data Centre - Data Delivery System

**A single cloud-based system for all SciLifeLab units, where data generated throughout each project can be delivered to the research groups in a fast, secure and simple way.**

> _This project is supported by EIT Digital, activity number 19390. This deliverable consists of design document and implementation report of application and validation of VEIL.AI technology in SciLifeLab context in Sweden._

The Delivery Portal consists of two components:

* The _backend api_ handling the requests and the logic behind the scenes.
  * <https://github.com/ScilifelabDataCentre/dds_web> (this repository)
* The _command line interface (CLI)_. This will be used for data delivery within larger projects
and/or projects resulting in the production of large amounts of data, e.g. sequence data.
  * <https://github.com/ScilifelabDataCentre/dds_cli>

The backend interface is built using [Flask](https://flask.palletsprojects.com/en/2.0.x/).

---
## Development
<br>

### Running with Docker

When developing this software, we recommend that you run the web server locally using Docker.
You can download Docker here: <https://docs.docker.com/get-docker/>

Then, fork this repository and clone to your local system.
In the root folder of the repo, run the server as follows:

```bash
docker-compose up
```

This command will orchestrate the building and running of two containers:
one for the SQL database (`mariadb`) and one for the application.

If you prefer, you can run the web servers in 'detached' mode with the `-d` flag, which does not block your terminal.
If using this method, you can stop the web server with the command `docker-compose down`.
<br><br>

### Python debugger inside docker
It's possible to use the interactive debugging tool `pdb` inside Docker with this method:
1. Edit the `docker-compose.yml` and for the `backend` service, add:
```
  tty: true
  stdin_open: true
```
just under
```
  ports:
    - 127.0.0.1:5000:5000
```

2. Put `import pdb; pdb.set_trace()` in the python code where you would like to activate the debugger.
3. Run with docker-compose as normal.
4. Find out the id of the container running the `backend`.
```
docker container ls
```
5. Attach to the running backend container:
```
docker container attach <container_id/name>
```
<br>

### Config settings

When run from the cloned repo, all settings are set to default values.
These values are publicly visible on GitHub and **should not be used in production!**
<br><br>

> :exclamation: <br> 
> At the time of writing, upload within projects created in the development database will most likely not work. <br>
> To use the upload functionality with the `CLI`, first create a project.

### Database changes

> :heavy_exclamation_mark: Do your database changes in `models.py` while the containers are running (`docker-compose up`). Do not restart them to regenerate the database.

If you modify the database models (e.g. tables or indexes), you must create a migration for the changes. We use `Alembic` (via `flask-migrate`) which compares our database models with the running database to generate a suggested migration.

Run the command `flask db migrate -m <commit message/name>` in the running backend:

```bash
docker exec dds_backend flask db migrate -m <commit message/name>
```

This will create a migration in the folder `migrations/versions`. Confirm that the changes in the file match the changes you did, otherwise change the `upgrade` and `downgrade` functions as needed. Keep an eye out for changes to the `apscheduler` tables and indexes, and make sure they are not included in the migration. Once the migration looks ok, test it by running `flask db upgrade` in the backend:

```bash
docker exec dds_backend flask db upgrade
```

Finally, confirm that the database looks correct after running the migration and commit the migration file to git. Note that you need to run `black` on the generated migration file. 

### Database issues while running `docker-compose up`

If you run into issues with complaints about the db while running `docker-compose up` you can try to reset the containers by running `docker-compose down` before trying again. If you still have issues, try cleaning up containers and volumes manually.

> :warning: These commands will remove _all_ containers and volumes!
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

---
<br>

## Production

When running in production, you will likely want to manually build and run the two containers.
Whilst in `docker-compose.yml` the web server is run by Flask (`command: python3 app.py`),
the default server in the container is `gunicorn` (`CMD ["gunicorn", "app:app"]`).

In addition to using `gunicorn` to serve files and running the MySQL database separately,
you will also need to overwrite all (or most) of the default configuration values.
<br><br>

### Environment variables

In the root of the repo you will find a file called `.env` - this sets the default values used for things like SQL database usernames and passwords, as well as file paths for uploads, downloads and more.

These values can be overwritten by setting as environment variables.
Copy the lines that you need to change and add to your `~/.bashrc` file, appending the `export` command.
For example:

```bash
export DDS_MYSQL_ROOT_PASS="your_custom_password"
export DDS_MYSQL_USER="your_custom_user"
export DDS_MYSQL_PASS="your_custom_password"
```

If you prefer, you can make a copy of the `.env` file somewhere and make edits there.
Then use the `--env-file` argument when running `docker-compose`, eg:

```bash
docker-compose --env-file ~/my_setup.env up
```
<br>

### Config file

In addition to the above, an environment variable `DDS_APP_CONFIG` can be used.
This should be a path to a config file with variables that overwrite the defaults set in `dds_web/config.py`.

For example:

```bash
SITE_NAME = "My Custom Data Delivery System"
SECRET_KEY = "some-mega-random-string"
SQLALCHEMY_DATABASE_URI = "mysql+pymysql://TEST_USER:TEST_PASSWORD@db/DeliverySystem"
```
<br>

### Flask env

Finally, an environment variable `FLASK_ENV` can be set as either `development` or `production`.
From the [Flask docs](https://flask.palletsprojects.com/en/2.0.x/config/#environment-and-debug-features):

> Setting `FLASK_ENV` to development will enable debug mode.
> flask run will use the interactive debugger and reloader by default in debug mode.

This variable should be set to `production` when running in production.

### Upgrades

Whenever you upgrade to a newer version, start by running `flask db upgrade` to make sure that the database schema is up-to-date.
