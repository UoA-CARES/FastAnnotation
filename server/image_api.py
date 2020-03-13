import base64
import os

from flask import Blueprint
from flask import jsonify
from flask import request
from flask_negotiate import produces, consumes
from mysql.connector.errors import DatabaseError

import server.utils as utils
from server.server_config import DatabaseInstance
from server.server_config import ServerConfig

image_blueprint = Blueprint('image_blueprint', __name__)

db = DatabaseInstance()


@image_blueprint.route("", methods=['GET'])
@produces('application/json')
@consumes('application/json')
def get_bulk_images():
    content = request.get_json()
    if "ids" not in content:
        response = jsonify(
            {"err": "Submitted content does not fit expected structure"})
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
        response = jsonify(
            {"err": "Submitted content does not fit expected structure"})
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


@image_blueprint.route("<int:iid>/annotation", methods=['POST'])
@produces('application/json')
@consumes('application/json')
def add_annotation_to_image(iid):
    content = request.get_json()

    i = 0
    for row in content["annotations"]:
        info = row['info']
        mask = utils.decode_mask(row['mask'], info['source_shape'])

        mask_path = os.path.join(
            ServerConfig.DATA_ROOT_DIR,
            "annotation",
            str(iid),
            "trimaps",
            "layer_%d.png" % i)
        info_path = os.path.join(
            ServerConfig.DATA_ROOT_DIR,
            "annotation",
            str(iid),
            "xmls",
            "layer_%d.xml" % i)

        query = "REPLACE INTO instance_seg_meta (image_id, mask_path, info_path, class_name) VALUES (%s,%s,%s,%s)"
        db.query(query, (iid, mask_path, info_path, info["class_name"]))

        utils.save_mask(mask, mask_path)
        utils.save_info(info, info_path)
        i += 1

    response = jsonify({"success": True, "id": iid})
    response.status_code = 200
    return response


@image_blueprint.route("<int:iid>/annotation", methods=['DELETE'])
def delete_annotations_for_image(iid):
    query = "DELETE FROM instance_seg_meta "
    query += "WHERE image_id = %s"
    try:
        db.query(query, (iid,))
    except DatabaseError as e:
        response = jsonify({"err_code": e.errno, "err_msg": e.msg})
        response.status_code = 400
    else:
        response = jsonify(success=True)
        response.status_code = 200
    return response


@image_blueprint.route("<int:iid>/annotation", methods=['GET'])
@produces('application/json')
def get_annotations_for_image(iid):
    query = "SELECT * FROM instance_seg_meta "
    query += "WHERE image_id = %s"
    results, _ = db.query(query, (iid,))

    body = []
    for row in results:
        mask = utils.load_mask(row[2])
        info = utils.load_info(row[3])
        annotation = {}
        annotation['mask'] = utils.encode_mask(mask)
        annotation['info'] = info
        body.append(annotation)

    body = {"image_id": iid, "annotations": body}
    response = jsonify(body)
    response.status_code = 200
    return response
