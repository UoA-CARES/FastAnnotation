import base64
import os
from pathlib import Path

import cv2
import numpy as np
from flask import Blueprint
from flask import jsonify
from flask import request
from flask_negotiate import produces, consumes
from mysql.connector.errors import DatabaseError

from server.server_config import DatabaseInstance
from server.server_config import ServerConfig

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
        response = jsonify({"ids": success_ids})
        response.status_code = 201
    elif not success_ids:
        response = jsonify({"errors": error_msgs})
        response.status_code = 400
    else:
        response = jsonify({"ids": success_ids,
                            "errors": error_msgs})
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


@project_blueprint.route("<int:pid>/images", methods=['GET'])
@produces('application/json')
@consumes('application/json')
def get_project_images(pid):
    content = request.get_json()

    query = "SELECT image_id FROM fadb.image "
    query += "WHERE project_fid = %s"

    if "filter" in content:
        filter_details = content["filter"]
        for key in filter_details:
            if key in ServerConfig.IMAGE_FILTER_MAP and filter_details[
                    key] in ServerConfig.IMAGE_FILTER_MAP[key]:
                query += " and " + \
                    ServerConfig.IMAGE_FILTER_MAP[key][filter_details[key]]

    if "order" in content:
        order = content["order"]
        if "by" in order:
            if order["by"] in ServerConfig.IMAGE_ORDER_BY_MAP:
                query += " ORDER BY " + \
                    ServerConfig.IMAGE_ORDER_BY_MAP[order["by"]]
                if "ascending" in order:
                    query += " asc" if bool(order["ascending"]) else "desc"
                else:
                    query += " asc"
    results, _ = db.query(query, (pid,))
    response = jsonify({"ids": [x[0] for x in results]})
    response.status_code = 200
    return response


@project_blueprint.route("<int:pid>/images", methods=['POST'])
@consumes('application/json')
def add_project_images(pid):
    content = request.get_json()

    if not isinstance(content, list):
        content = [content]

    success_ids = []
    error_msgs = []
    for row in content:
        array = np.fromstring(base64.b64decode(row["image"]), np.uint8)
        img = cv2.imdecode(array, cv2.IMREAD_COLOR)
        img_dir = os.path.join(
            ServerConfig.DATA_ROOT_DIR,
            "images",
            str(pid))
        Path(img_dir).mkdir(parents=True, exist_ok=True)
        img_path = os.path.join(
            img_dir,
            row["name"] +
            ServerConfig.DEFAULT_IMAGE_EXT)

        query = "INSERT INTO image (project_fid, image_path, image_name) "
        query += "VALUES (%s, %s, %s);"
        try:
            _, id = db.query(query, (pid, img_path, row["name"]))
        except DatabaseError as e:
            msg = "Unknown Error"
            if e.errno == 1062:
                msg = "Uploaded file already exists called %s" % row["name"]
            error_msgs.append({"err_code": e.errno, "err_msg": msg})
        else:
            cv2.imwrite(img_path, img)
            success_ids.append(id)

    # Increment unlabeled image count
    if len(success_ids) > 0:
        query = "UPDATE project SET unlabeled_count = unlabeled_count + %s WHERE project_id = %s"
        try:
            db.query(query, (len(success_ids), pid))
        except DatabaseError as e:
            msg = "Unknown Error"
            error_msgs.append({"err_code": e.errno, "err_msg": msg})

    if not error_msgs:
        response = jsonify({"ids": success_ids})
        response.status_code = 201
    elif not success_ids:
        response = jsonify({"errors": error_msgs})
        response.status_code = 400
    else:
        response = jsonify({"ids": success_ids,
                            "errors": error_msgs})
        response.status_code = 201
    return response
