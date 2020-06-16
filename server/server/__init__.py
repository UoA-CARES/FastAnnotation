import os

from flask import Flask
from flask_restful import Api
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_restful_swagger import swagger

load_dotenv()

app = Flask(__name__)
api = swagger.docs(Api(app), apiVersion='0.1')

# Generate the connection string in one line to avoid storing sensitive info as variables, and hopefully reducing the
# chances of it getting logged.
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://{user}:{password}@{host}/{name}'.format(
    user=os.environ.get('DB_USER'),
    password=os.environ.get('DB_PASSWORD'),
    host=os.environ.get('DB_HOST'),
    name=os.environ.get('DB_NAME'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

import server.image.image
import server.project.project
import server.annotation.annotation
