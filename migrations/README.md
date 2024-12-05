# Making database changes - Adding a new migration

If you modify the database models (e.g. tables or indexes), you must create a migration for the changes. We use `Alembic` (via `flask-migrate`) which compares our database models with the running database to generate a suggested migration.

This document explains how to generate new database migration. 

## Steps for Generating Migrations

### 1. Start the Containers

Before making any changes to the database models, ensure the containers are running locally.

```bash
docker compose up # See root README for information regarding the different profiles
```

### 2. Modify the Database Models

Edit the `models.py` file to reflect the changes you need. This might include:

- Adding new tables or columns
- Modifying existing fields
- Deleting tables or columns

### 3. Create a new migration 

To create the migration, pick **one of the following options**. This will create a migration in the folder `migrations/versions`.

#### Option A

```bash
# 1. Enter the container
docker exec -it dds_backend /bin/sh

# 2. Generate the migration
flask db migrate -m <migration name>
```

#### Option B

```bash
# **Outside** of the container, run the following command
# This will generate the migration
docker exec dds_backend flask db migrate -m <migration name>
```

### 4. Review the Generated Migration File

Now, a new migration will have been generated in the `migrations/versions` directory. **Review this file carefully** to ensure it correctly represents your intended changes. If not, change the `upgrade` and `downgrade` functions as needed. 
    
> **NB!** Keep an eye out for changes to the `apscheduler` tables and indexes, and **make sure they are not included in the migration**. 
> Apscheduler is no longer used for the cronjobs, but are listed in the requirements still. This note will be removed once we have removed `apscheduler` all together. 

For reference on available operations and customization options, check the [Alembic Documentation](https://alembic.sqlalchemy.org/en/latest/ops.html).


### 5. Test the migration

Once the migration looks ok, test it using one of the following options. Confirm that the database looks correct.

#### Option A

```bash
# 1. Enter the container
docker exec -it dds_backend /bin/sh

# 2. Run the database upgrade
flask db upgrade
``` 

#### Option B

```bash
# **Outside** of the container, run the following command
# This will run the migration and upgrade the database
docker exec dds_backend flask db upgrade
```

### 6. Commit the Migration File

Finally, commit the migration file to git. 


## How to start over

If you want to start over, e.g. if something went wrong when following the steps outlined above, follow the steps below.

1. Restore the content of `migrations/versions`:

    a) Remove the new migrations file(s)
    b) Run `git restore` on the `migrations/versions` folder

2. Reset the container: `docker compose down`
3. Remove `flask init-db $$DB_TYPE &&` in the `docker-compose.yml` file. This will prevent the population of the database and instead allow the install of the old schema. 
4. Start the container again: `docker-compose up`
5. Follow the [Steps for Generating Migrations](#steps-for-generating-migrations) section

## Database issues while running `docker-compose up`

If you run into issues with complaints about the db while running `docker compose up` you can try to reset the containers by running `docker compose down` before trying again. If you still have issues, try cleaning up containers and volumes manually.

> ⚠️ These commands will remove _all_ containers and volumes!
> If you are working on other projects please be more selective.

```bash
docker rm $(docker ps -a -q) -f
docker volume prune
```

Then run `docker compose up` as normal. The images will be rebuilt from scratch before launch.

If there are still issues, try deleting the `pycache` folders and repeat the above steps.
