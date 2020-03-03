import os
import base64

from flask import Blueprint
from flask_negotiate import produces, consumes
from flask import jsonify
from server.server_config import DatabaseInstance

image_blueprint = Blueprint('image_blueprint', __name__)

db = DatabaseInstance()


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
                'name': name,
                'image': encoded_image.decode('utf-8')
            })
            return jsonify(body[0])

    body.append({"err": "Resource not found."})
    response = jsonify(body)
    response.status = 404
    return response
