from flask import Flask
from flask import jsonify
from datetime import datetime
from server.server_config import ServerConfig
from database.database import Database


app = Flask(__name__)

fadb = Database(ServerConfig())


@app.route("/heartbeat")
def heartbeat():
    response = str(datetime.now())
    return jsonify(response)


@app.route("/project", methods=['GET'])
def get_projects():
    results = fadb.query("SELECT project_id from project")
    results = [x[0] for x in results]
    results = {'ids': results}
    # Return all Project ids
    return jsonify(results)


@app.route("/project/<int:id>", methods=['GET'])
def get_project(id):
    query = "SELECT * from project "
    query += "WHERE project_id = " + str(id)
    results = fadb.query(query)
    return jsonify(fadb.form_results('project', results))


if __name__ == "__main__":
    app.run()
