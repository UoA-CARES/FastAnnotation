## Requirements
* python 3.6+
* Docker and Docker Compose

## Installation

Install dependencies using the following, ideally within a virtual environment if it is for development
```
>> pip install -r requirements.txt 
```

## Development
```docker-compose.yml``` is provided to run a PostgreSQL database locally for development. This database should only
be used for development. A managed database should be used in production e.g. AWS RDS.

### Quickstart
Run the quickstart from the server base directory
```
>> cd server/server
```
Install dependencies
```
>> pip install -r requirements.txt
```
Run PostgreSQL locally
```
>> cd ..
>> docker-compose up
```
Create a `server/server/.env` file with database credentials, replacing items in `<>` as appropriate.
```.env
DB_USER=<database user>
DB_PASSWORD=<database password>
DB_HOST=<database host>
DB_NAME=<database name>
```
Running migrations and starting the serer should be performed from the `server/server` directory

Specify flask application
```
>> export FLASK_APP=__init__.py
```
Apply migrations
```
>> flask db upgrade
```
Start server
```
>> flask run
```
The OpenAPI spec should now be available at `http://localhost:5000/api/spec.html`
### Adding a dependency
If you need to add a dependency it should be added to the requirements.txt file.
```
>> pip install my-new-dependency
...
>> pip freeze > requirements.txt
```


### Database Credentials
Database credentials and other secrets should never be committed. Create a ```.env``` file inside the server directory with the following contents, replacing items inside `<>` as appropriate
```.env
DB_USER=<database user>
DB_PASSWORD=<database password>
DB_HOST=<database host>
DB_NAME=<database name>
```
The application will automatically load the above credentials into the environment at startup. The `.env` file should not be commited.

The connection string is constructed in ```__init__.py``` as
```
postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}
```

### Running PostgreSQL locally for development
Start with
```
>> docker-compose up
```

Stop with
```
>> docker-compose down
```

If you want to delete all data (clear the attached volume), use the following instead
```
>> docker-compose down -v
```

### Testing
Run all tests
```
>> pytest
```

Tests are stored in `test_*.py` files.
### Migrations
First we need to tell Flask the application entrypoint
```
>> cd server
>> export FLASK_APP=__init__.py
```

Migrations are handled using flask-migrate. If you update or create models, you should create a migration
```
>> flask db migrate -m "Some informative name for the migration"
```
This will automatically create a migration file inside the `migrations/` directory. Not all changes can be detected. In particular, 
Alembic is currently unable to detect table name changes, column name changes, or anonymously named constraints. The autodetect 
functionality and limitations are [here](https://alembic.sqlalchemy.org/en/latest/autogenerate.html#what-does-autogenerate-detect-and-what-does-it-not-detect).

All pending migrations can be applied with
```
>> flask db upgrade
```

## Production
Should use a managed DB, e.g. AWS RDS, with backups enabled.
Set database credentials as environment variables.
...


## TODO 
* Authentication and authorisation mechanisms
* Associate annotation with image as being either human or machine generated
* Allow clients, e.g. machine clients running training code, to specify image priorities
* Allow client to query for the next image that they should be annotating
* Implement controls so that multiple human annotators do not end up annotating the same
image at the same time
