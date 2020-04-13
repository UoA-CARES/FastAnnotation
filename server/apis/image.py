import base64

import server.utils as utils
from flask import request
from flask_restplus import Namespace, Resource, fields, marshal
from mysql.connector.errors import DatabaseError

from server.core.common_dtos import common_store
from server.server_config import DatabaseInstance

api = Namespace('images', description='Image related operations')

db = DatabaseInstance()

api.models.update(common_store.get_dtos())

image = api.model('image', {
    'id': fields.Integer(attribute='image_id', required=False, description='The image identifier'),
    'name': fields.String(attribute='image_name', required=False, description='The image name'),
    'ext': fields.String(attribute='image_ext', required=False, description="The file extension of the image"),
    'is_locked': fields.Boolean(required=False, description="A flag indicating whether the image is locked"),
    'is_labeled': fields.Boolean(required=False, description="A flag indicating whether the image is labeled"),
    'image_data': fields.String(required=False, description="The encoded image data")
})

bulk_images = api.model('bulk_images', {
    'images': fields.List(fields.Nested(image))
})


annotation = api.model('annotation', {
    'id': fields.Integer(
        attribute="annotation_id",
        required=False,
        description="The annotation identifier"),
    'mask_data': fields.String(
        required=True,
        description="The encoded mask data"),
    'bbox': fields.List(
        fields.Integer,
        required=True,
        description="The bounding box coordinates"),
    'shape': fields.List(
        fields.Integer,
        required=True,
        description="The dimensions of the image in pixels"),
    'class_name': fields.String(
        required=True,
        description="The name of the class associated with this annotation")})

bulk_annotations = api.model('bulk_annotations', {
    'annotations': fields.List(fields.Nested(annotation))
})


@api.route("/<int:iid>")
class Image(Resource):
    def get(self, iid):
        """
        Gets an image as referenced by its identifier.
        """
        query = "SELECT image_id, image_path, image_name, image_ext, is_locked, is_labeled FROM image "
        query += "WHERE image_id = %s"

        try:
            result = db.query(query, (iid,))[0]
            response = result[0]
        except DatabaseError as e:
            response = {
                "action": "failed",
                "error": {
                    "code": 400,
                    "message": e.msg
                }
            }
            code = 400
        except IndexError:
            response = {
                "action": "failed",
                "error": {
                    "code": 404,
                    "message": "Resource not found."
                }
            }
            code = 404

        except BaseException as e:
            response = {
                "action": "failed",
                "error": {
                    "code": 500,
                    "message": str(e)
                }
            }
            code = 500
        else:
            if response["image_ext"] == ".jpg":
                with open(response["image_path"], "rb") as img_file:
                    encoded_image = base64.b64encode(img_file.read())
                    response["image_data"] = encoded_image.decode('utf-8')
            code = 200

        if code == 200:
            return marshal(response, image), code
        else:
            return marshal(response, api.models["generic_response"]), code

    @api.marshal_with(api.models["generic_response"])
    @api.expect(image)
    def put(self, iid):
        """
        Update an images meta parameters.
        """

        content = request.json

        query = "UPDATE image SET"
        params = []
        if "name" in content:
            query += " image_name = %s"
            params.append(content["name"])
        if "ext" in content:
            query += " image_ext = %s"
            params.append(content["ext"])
        if "is_locked" in content:
            query += " is_locked = %s"
            params.append(content["is_locked"])
        if "is_labeled" in content:
            query += " is_labeled = %s"
            params.append(content["is_labeled"])

        query += " WHERE image_id = %s"
        params.append(iid)
        try:
            db.query(query, (params,))
        except DatabaseError as e:
            response = {
                "action": "failed",
                "error": {
                    "code": 400,
                    "message": e.msg
                }
            }
            code = 400
        except BaseException as e:
            response = {
                "action": "failed",
                "error": {
                    "code": 500,
                    "message": str(e)
                }
            }
            code = 500
        else:
            response = {
                "action": "updated",
                "id": iid
            }
            code = 200
        return response, code

    @api.marshal_with(api.models["generic_response"])
    def delete(self, iid):
        """
        Delete an image as referenced by its identifier.
        """

        q_delete_annotations = "DELETE from instance_seg_meta WHERE image_id = %s"
        query = "DELETE from image WHERE image_id = %s"

        try:
            db.query(q_delete_annotations, (iid,))
            db.query(query, (iid,))
        except DatabaseError as e:
            response = {
                "action": "failed",
                "error": {
                    "code": 400,
                    "message": e.msg
                }
            }
            code = 400
        except BaseException as e:
            response = {
                "action": "failed",
                "error": {
                    "code": 500,
                    "message": str(e)
                }
            }
            code = 500
        else:
            response = {
                "action": "deleted",
                "id": iid
            }
            code = 200
        return response, code


@api.route("/<int:iid>/annotation")
class ImageAnnotationList(Resource):
    def get(self, iid):
        """
        Gets all the annotations associated with an image.
        """

        query = "SELECT annotation_id, mask_path, info_path, class_name FROM instance_seg_meta "
        query += "WHERE image_id = %s"
        try:
            result = db.query(query, (iid,))[0]
        except DatabaseError as e:
            response = {
                "action": "failed",
                "error": {
                    "code": 400,
                    "message": e.msg
                }
            }
            code = 400
        except BaseException as e:
            response = {
                "action": "failed",
                "error": {
                    "code": 500,
                    "message": str(e)
                }
            }
            code = 500
        else:
            response = []
            for row in result:
                mask = utils.load_mask(row["mask_path"])
                info = utils.load_info(row["info_path"])
                row["mask_data"] = utils.encode_mask(mask)
                row["shape"] = info["source_shape"]
                row["bbox"] = info["bbox"]
                response.append(row)

            response = {"annotations": response}
            code = 200
        if code == 200:
            return marshal(response, bulk_annotations), code
        else:
            return marshal(response, api.models["generic_response"]), code

    @api.marshal_with(api.models["bulk_response"])
    @api.expect(bulk_annotations)
    def post(self, iid):
        """
        A bulk operation for adding annotations to an image.
        """

    def delete(self, iid):
        """
        Deletes all annotations from an image.
        """
