import base64

from flask import Blueprint
from flask import jsonify
from flask import request
from flask_negotiate import produces, consumes

from server.server_config import DatabaseInstance

image_blueprint = Blueprint('image_blueprint', __name__)

db = DatabaseInstance()


@image_blueprint.route("", methods=['GET'])
@produces('application/json')
@consumes('application/json')
def get_bulk_images():
    content = request.get_json()
    if "ids" not in content:
        response = jsonify({"err": "Submitted content does not fit expected structure"})
        response.status_code = 400
        return response

    image_ids = content["ids"]

    query = "SELECT image_id, image_path, image_name, image_ext FROM image "
    query += "WHERE image_id in ("
    query += ','.join(["%s"] * len(image_ids))
    query += ")"
    result, _ = db.query(query, tuple(image_ids))

    body = []

    for row in result:
        iid, path, name, ext = row
        if ext == '.jpg':
            with open(path, "rb") as img_file:
                encoded_image = base64.b64encode(img_file.read())
            body.append({
                'name': name,
                'image': encoded_image.decode('utf-8')
            })
    return jsonify(body)


@image_blueprint.route("meta", methods=['GET'])
@produces('application/json')
@consumes('application/json')
def get_bulk_image_metas():
    content = request.get_json()
    if "ids" not in content:
        response = jsonify({"err": "Submitted content does not fit expected structure"})
        response.status_code = 400
        return response

    image_ids = content["ids"]

    query = "SELECT image_id, image_name, image_ext, is_locked, is_labelled FROM image "
    query += "WHERE image_id in ("
    query += ','.join(["%s"] * len(image_ids))
    query += ")"
    result, _ = db.query(query, tuple(image_ids))

    body = []

    for row in result:
        iid, name, ext, is_locked, is_labelled = row
        body.append({
            'id': iid,
            'name': name,
            'ext': ext,
            'is_locked': bool(is_locked),
            'is_labelled': bool(is_labelled)
        })
    return jsonify(body)


@image_blueprint.route("<int:iid>", methods=['GET'])
@produces('application/json')
def get_image_by_id(iid):
    query = "SELECT image_path, image_name, image_ext FROM image "
    query += "WHERE image_id = %s"

    result, _ = db.query(query, (iid,))
    body = []

    if result:
        path, name, ext = result[0]
        if ext == '.jpg':
            with open(path, "rb") as img_file:
                encoded_image = base64.b64encode(img_file.read())
            body.append({
                'id': iid,
                'name': name,
                'image': encoded_image.decode('utf-8')
            })
            return jsonify(body[0])

    body.append({"err": "Resource not found."})
    response = jsonify(body)
    response.status = 404
    return response


@image_blueprint.route("<int:iid>/meta", methods=['GET'])
@produces('application/json')
def get_image_meta_by_id(iid):
    query = "SELECT image_name, image_ext, is_locked, is_labelled FROM image "
    query += "WHERE image_id = %s"

    result, _ = db.query(query, (iid,))
    body = {}

    if result:
        name, ext, is_locked, is_labelled = result[0]
        body['id'] = iid
        body['name'] = name
        body['ext'] = ext
        body['is_locked'] = bool(is_locked)
        body['is_labelled'] = bool(is_labelled)

        return jsonify(body)

    body = {"err": "Resource not found."}
    response = jsonify(body)
    response.status = 404
    return response


@image_blueprint.route("<int:iid>/lock", methods=['PUT'])
@produces('application/json')
def lock_image_by_id(iid):
    query = "SELECT image_name, image_ext, is_locked, is_labelled FROM image "
    query += "WHERE image_id = %s"

    result, _ = db.query(query, (iid,))
    if not result:
        body = {"err": "Resource not found."}
        response = jsonify(body)
        response.status_code = 404
        return response

    name, ext, is_locked, is_labelled = result[0]

    if bool(is_locked):
        body = {"err": "Resource is already locked."}
        response = jsonify(body)
        response.status_code = 403
        return response

    query = "UPDATE image SET is_locked = b'1' WHERE image_id = %s"
    db.query(query, (iid,))
    response = jsonify({"success": True, "id": iid})
    response.status_code = 200
    return response


@image_blueprint.route("<int:iid>/unlock", methods=['PUT'])
@produces('application/json')
def unlock_image_by_id(iid):
    query = "SELECT image_name, image_ext, is_locked, is_labelled FROM image "
    query += "WHERE image_id = %s"

    result, _ = db.query(query, (iid,))
    if not result:
        body = {"err": "Resource not found."}
        response = jsonify(body)
        response.status_code = 404
        return response

    query = "UPDATE image SET is_locked = b'0' WHERE image_id = %s"
    db.query(query, (iid,))
    response = jsonify({"success": True, "id": iid})
    response.status_code = 200
    return response
