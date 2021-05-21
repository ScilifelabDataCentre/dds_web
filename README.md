# SciLifeLab Data Centre - Data Delivery System

**A single cloud-based system for all SciLifeLab facilities, where data generated throughout each project can be delivered to the research groups in a fast, secure and simple way.**

> _This project is supported by EIT Digital, activity number 19390. This deliverable consists of design document and implementation report of application and validation of VEIL.AI technology in SciLifeLab context in Sweden._

The Delivery Portal consists of two components:

* The _web interface_ where the research groups and facilities will be able to follow the data
delivery progress. The web interface will also be an option for the delivery within small
projects, e.g. small and/or few files.
  * <https://github.com/ScilifelabDataCentre/dds_web> (this repository)
* The _command line interface (CLI)_. This will be used for data delivery within larger projects
and/or projects resulting in the production of large amounts of data, e.g. sequence data.
  * <https://github.com/ScilifelabDataCentre/dds_cli>

The web interface is built using [Flask](https://flask.palletsprojects.com/en/2.0.x/).

## Development

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

### Compiling CSS & JS

The website uses SASS / SCSS for its stylesheets, allowing customisation of Bootstrap styles.
To manage the CSS and JavaScript packages, we use `npm`.

#### Using Docker

It's complex to be building the CSS dynamically during development from within `docker-compose.yml`,
but it is possible to use a separate Docker image in another tab.

To make this easy, there is a convenience script in the root folder called `compile_css.sh`.
Running this will launch `npm` inside a container which will install all packages, compile CSS
and then watch for any changes to the source SCSS files. Newly compiled files will be created on save.
When you're done, just `cmd+c` to exit.

Using Docker is the recommended way to do this, as the packages installed will be more consistent.

#### Using `npm`

If you have [NodeJS](https://nodejs.org/en/download/) installed you can just run `npm` locally without Docker.

The first time you run the website, you will need to initialise the required packages and compile the CSS:

```bash
cd dds_web/static/
npm install
npm run css
```

To get `npm` to automatically recompile the CSS every time you change something,
run `npm run watch` in the `static/` folder.

Using Docker is preferred, as the installation may resolve different files with different
operating systems / node installations. This can lead to large diffs in the `package-lock.json` file.

### Config settings

When run from the cloned repo, all settings are set to default values.
These values are publicly visible on GitHub and **should not be used in production!**

At the time of writing, much of the functionality will not work with the defaults.
Please see the _Production_ section below for how to set what you need.

### Database changes

If the database is modified, you will need to rebuild the containers from scratch.

First, remove all docker containers and volumes

> :warning: These commands will remove _all_ containers and volumes!
> If you are working on other projects please be more selective.

```bash
docker rm $(docker ps -a -q) -f
docker volume prune
```

Then run `docker-compose up` as normal. The images will be rebuilt from scratch before launch.

If there are still issues, try deleting the `pycache` folders and repeat the above steps.

## Production

When running in production, you will likely want to manually build and run the two containers.
Whilst in `docker-compose.yml` the web server is run by Flask (`command: python3 app.py`),
the default server in the container is `gunicorn` (`CMD ["gunicorn", "app:app"]`).
The other difference is that the docker image comes with compiled CSS files ready to go,
but the docker-compose script mounts the local volume. So for development you need to run `npm`
but for production there is no need.

In addition to using `gunicorn` to serve files and runing the MySQL database separately,
you will also need to overwrite all (or most) of the default configuration values.

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
docker-compose up --env-file ~/my_setup.env
```

### Config file

In addition to the above, an environment variable `DDS_APP_CONFIG` can be used.
This should be a path to a config file with variables that overwrite the defaults set in `dds_web/config.py`.

For example:

```bash
SITE_NAME = "My Custom Data Delivery System"
SECRET_KEY = "some-mega-random-string"
SQLALCHEMY_DATABASE_URI = "mysql+pymysql://TEST_USER:TEST_PASSWORD@db/DeliverySystem"
DDS_SAFE_SPRING_PROJECT = "YOUR-PROJECT-ID"
```

### Flask env

Finally, an environment variable `FLASK_ENV` can be set as either `development` or `production`.
From the [Flask docs](https://flask.palletsprojects.com/en/2.0.x/config/#environment-and-debug-features):

> Setting `FLASK_ENV` to development will enable debug mode.
> flask run will use the interactive debugger and reloader by default in debug mode.

This variable should be set to `production` when running in production.
