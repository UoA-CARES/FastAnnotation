from flask import Flask
from flask import jsonify
from flask import request
from flask import abort
from flask_negotiate import produces, consumes
from datetime import datetime
from server.server_config import ServerConfig
from database.database import Database
from mysql.connector.errors import DatabaseError
from mysql.connector.errors import ProgrammingError

app = Flask(__name__)

fadb = Database(ServerConfig())


@app.route("/heartbeat")
def heartbeat():
    response = str(datetime.now())
    return jsonify(response)


@app.route("/project", methods=['GET'])
@produces('application/json')
def get_projects():
    results = fadb.query("SELECT project_id FROM project")
    results = [x[0] for x in results]
    results = {'ids': results}
    # Return all Project ids
    return jsonify(results)


@app.route("/project/<int:id>", methods=['GET'])
@produces('application/json')
def get_project(id):
    query = "SELECT * FROM project "
    query += "WHERE project_id = %s"
    results = fadb.query(query, (id,))
    return jsonify(fadb.rows_to_json('project', results))


@app.route("/project", methods=['POST'])
@consumes('application/json')
def add_project():
    content = request.get_json()
    if not isinstance(content, list):
        content = [content]

    success_ids = []
    error_msgs = []
    for item in content:
        query = "INSERT INTO project ("
        query += ",".join(item.keys())
        query += ") "
        query += "VALUES ("
        query += ",".join(["%s"] * len(item))
        query += ");"
        try:
            fadb.query(query, tuple(item.values()))
            id = fadb.get_last_row_id()
            success_ids.append(id)
        except DatabaseError as e:
            error_msgs.append(
                {"request": item, "err_code": e.errno, "err_msg": e.msg})
        except BaseException as e:
            error_msgs.append(
                {"request": item, "err_code": 500, "err_msg": "Unknown Server Fault."})

    if not error_msgs:
        response = jsonify({"Created Ids": success_ids})
        response.status_code = 201
    elif not success_ids:
        response = jsonify({"Bad Requests": error_msgs})
        response.status_code = 400
    else:
        response = jsonify({"Created Ids": success_ids,
                            "Bad Requests": error_msgs})
        response.status_code = 201

    return response


@app.route("/project/<int:id>", methods=['DELETE'])
def del_project(id):
    query = "DELETE FROM project WHERE project_id = %s"
    try:
        fadb.query(query, (id,))
    except DatabaseError as e:
        response = jsonify({"err_code": e.errno, "err_msg": e.msg})
        response.status_code = 400
    else:
        response = jsonify(success=True)
        response.status_code = 200

    return response


if __name__ == "__main__":
    app.run()
