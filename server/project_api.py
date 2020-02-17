import base64

import cv2
import numpy as np
from flask import Blueprint
from flask import jsonify
from flask import request
from flask_negotiate import produces, consumes
from mysql.connector.errors import DatabaseError

from server.server_config import DatabaseInstance

project_blueprint = Blueprint('project_blueprint', __name__)

db = DatabaseInstance()


@project_blueprint.route("", methods=['GET'])
@produces('application/json')
def get_projects():
    results = db.query("SELECT * FROM project")[0]
    return jsonify(db.rows_to_json('project', results))


@project_blueprint.route("<int:id>", methods=['GET'])
@produces('application/json')
def get_project(id):
    query = "SELECT * FROM project "
    query += "WHERE project_id = %s"
    results = db.query(query, (id,))[0]
    return jsonify(db.rows_to_json('project', results))


@project_blueprint.route("", methods=['POST'])
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
            _, id = db.query(query, tuple(item.values()))
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


@project_blueprint.route("<int:id>", methods=['DELETE'])
def del_project(id):
    query = "DELETE FROM project WHERE project_id = %s"
    try:
        db.query(query, (id,))
    except DatabaseError as e:
        response = jsonify({"err_code": e.errno, "err_msg": e.msg})
        response.status_code = 400
    else:
        response = jsonify(success=True)
        response.status_code = 200

    return response


@project_blueprint.route("<int:id>/images", methods=['GET'])
@produces('application/json')
def get_project_images(id):
    query = "SELECT image_id FROM fadb.image "
    query += "WHERE project_fid = %s"
    results, _ = db.query(query, (id,))
    response = jsonify({"ids": results})
    response.status_code = 200
    return response


@project_blueprint.route("<int:id>/images", methods=['POST'])
@consumes('application/json')
def add_project_images(id):
    content = request.get_json()

    if not isinstance(content, list):
        content = [content]

    for row in content:
        array = np.fromstring(base64.b64decode(row["image"]), np.uint8)
        img = cv2.imdecode(array, cv2.IMREAD_COLOR)



    return jsonify(True)
