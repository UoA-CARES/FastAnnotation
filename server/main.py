from datetime import date
from datetime import datetime

from flask import Flask
from flask import jsonify
from flask.json import JSONEncoder

from database.database import Database
from server.project_api import project_blueprint
from server.server_config import ServerConfig


class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        try:
            if isinstance(obj, date):
                return datetime.timestamp(obj)
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)
        return JSONEncoder.default(self, obj)


app = Flask(__name__)
app.json_encoder = CustomJSONEncoder
app.register_blueprint(project_blueprint, url_prefix='/projects')
app.config["db"] = Database(ServerConfig())


project_blueprint.config = {"Hello": "Hello"}


@app.route("/heartbeat")
def heartbeat():
    response = str(datetime.now())
    return jsonify(response)


if __name__ == "__main__":
    app.run()
