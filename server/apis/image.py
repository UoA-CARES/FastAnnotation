import base64
import os

import server.utils as utils
from flask import request
from flask_restplus import Namespace, Resource, fields, marshal
from mysql.connector.errors import DatabaseError

from server.core.common_dtos import common_store
from server.server_config import DatabaseInstance
from server.server_config import ServerConfig

api = Namespace('images', description='Image related operations')

db = DatabaseInstance()

api.models.update(common_store.get_dtos())

image = api.model(
    'image',
    {
        'id': fields.Integer(
            attribute='image_id',
            required=False,
            description='The image identifier'),
        'name': fields.String(
            attribute='image_name',
            required=False,
            description='The image name',
            example="image_123"),
        'ext': fields.String(
            attribute='image_ext',
            required=False,
            description="The file extension of the image",
            example=".jpg"),
        'is_locked': fields.Boolean(
            required=False,
            description="A flag indicating whether the image is locked"),
        'is_labeled': fields.Boolean(
            required=False,
            description="A flag indicating whether the image is labeled"),
        'image_data': fields.String(
            required=False,
            description="The encoded image data")})

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
        description="The bounding box coordinates",
        min_items=4,
        max_items=4,
        example=[0, 0, 200, 200]),
    'shape': fields.List(
        fields.Integer,
        required=True,
        description="The dimensions of the image in pixels",
        min_items=3,
        max_items=3,
        example=[1920, 1080, 3]),
    'class_name': fields.String(
        required=True,
        description="The name of the class associated with this annotation",
        example="class_1")})

bulk_annotations = api.model('bulk_annotations', {
    'image_id': fields.Integer(
        required=True,
        description="The identifier for the image associated with the attached annotations"),
    'annotations': fields.List(fields.Nested(annotation))
})

bulk_image_request = api.model('bulk_image_request', {'ids': fields.List(
    fields.Integer, required=True, description="The list of image ids to retrieve")})


@api.route("")
class ImageList(Resource):
    @api.response(200, "OK", bulk_images)
    @api.response(400, "Invalid Payload")
    @api.response(500, "Unexpected Failure", api.models["generic_response"])
    @api.expect(bulk_image_request)
    @api.param(
        'image-data',
        description='A flag indicating whether image data is required',
        type='boolean')
    def get(self):
        """
        A bulk operation for retrieving images by id.
        """
        content = request.json

        image_data_flag = request.args.get('image-data')
        if image_data_flag.lower() not in ("true", "false"):
            image_data_flag = True
        else:
            image_data_flag = image_data_flag.lower() == "true"

        query = "SELECT image_id, image_path, image_name, image_ext, is_locked, is_labeled FROM image "
        query += "WHERE image_id IN "
        query += "(%s)" % ",".join(str(x) for x in content["ids"])

        try:
            result = db.query(query)[0]
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
            images = []
            for row in result:
                if not image_data_flag:
                    pass
                elif row["image_ext"].lower() in (".jpg", ".jpeg", ".png"):
                    with open(row["image_path"], "rb") as img_file:
                        encoded_image = base64.b64encode(img_file.read())
                        row["image_data"] = encoded_image.decode('utf-8')
                images.append(row)
            response = {"images": images}
            code = 200

        if code == 200:
            return marshal(response, bulk_images), code
        else:
            return marshal(response, api.models["generic_response"]), code


@api.doc(params={"iid": "An id associated with an existing image."})
@api.route("/<int:iid>")
class Image(Resource):
    @api.response(200, "OK", image)
    @api.response(404, "Resource Not Found", api.models["generic_response"])
    @api.response(500, "Unexpected Failure", api.models["generic_response"])
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
                    "code": 500,
                    "message": e.msg
                }
            }
            code = 500
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
            return marshal(response, image, skip_none=True), code
        else:
            return marshal(
                response, api.models["generic_response"], skip_none=True), code

    @api.response(200, "OK", api.models["generic_response"])
    @api.response(400, "Invalid Payload", api.models["generic_response"])
    @api.response(500, "Unexpected Failure", api.models["generic_response"])
    @api.marshal_with(api.models["generic_response"], skip_none=True)
    @api.expect(image)
    def put(self, iid):
        """
        Update an images meta parameters.
        """

        #TODO: Update to raise 409 when lock is requested on already locked object

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

        if not params:
            response = {
                "action": "failed",
                "error": {
                    "code": 400,
                    "message": "No valid parameters provided for update."
                }
            }
            return response, 400

        query += " WHERE image_id = %s"
        params.append(iid)
        try:
            db.query(query, tuple(params))
        except DatabaseError as e:
            response = {
                "action": "failed",
                "error": {
                    "code": 500,
                    "message": e.msg
                }
            }
            code = 500
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

    @api.response(200, "OK", api.models["generic_response"])
    @api.response(500, "Unexpected Failure", api.models["generic_response"])
    @api.marshal_with(api.models["generic_response"], skip_none=True)
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
                    "code": 500,
                    "message": e.msg
                }
            }
            code = 500
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


@api.doc(params={"iid": "An id associated with an existing image"})
@api.route("/<int:iid>/annotation")
class ImageAnnotationList(Resource):
    @api.response(200, "OK", bulk_annotations)
    @api.response(500, "Unexpected Failure", api.models["generic_response"])
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
                    "code": 500,
                    "message": e.msg
                }
            }
            code = 500
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

            response = {"image_id": iid, "annotations": response}
            code = 200
        if code == 200:
            return marshal(response, bulk_annotations, skip_none=True), code
        else:
            return marshal(
                response, api.models["generic_response"], skip_none=True), code

    @api.response(200, "Partial Success", api.models["bulk_response"])
    @api.response(201, "Success", api.models["bulk_response"])
    @api.marshal_with(api.models["bulk_response"], skip_none=True)
    @api.expect(bulk_annotations)
    def post(self, iid):
        """
        A bulk operation for adding annotations to an image.
        """

        content = request.json

        query = "DELETE FROM instance_seg_meta WHERE image_id = %s"
        try:
            db.query(query, (iid,))
        except BaseException:
            pass

        i = 0
        code = 201
        results = []
        for row in content["annotations"]:
            try:
                mask = utils.decode_mask(row['mask_data'], row['shape'])

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

                query = "REPLACE INTO instance_seg_meta (image_id, mask_path, info_path, class_name)"
                query += " VALUES (%s,%s,%s,%s)"
                _, aid = db.query(
                    query, (iid, mask_path, info_path, row["class_name"]))

                utils.save_mask(mask, mask_path)
                utils.save_info(
                    shape=row["shape"],
                    bbox=row["bbox"],
                    class_name=row["class_name"],
                    filepath=info_path)
                i += 1
            except DatabaseError as e:
                response = {
                    "action": "failed",
                    "error": {
                        "code": 400,
                        "message": e.msg
                    }
                }
                results.append(response)
                code = 200
            except BaseException as e:
                response = {
                    "action": "failed",
                    "error": {
                        "code": 500,
                        "message": str(e)
                    }
                }
                results.append(response)
                code = 200
            else:
                response = {
                    "action": "created",
                    "id": aid
                }
                results.append(response)

        return {"results": results}, code

    @api.response(200, "OK", api.models["generic_response"])
    @api.response(500, "Unexpected Failure", api.models["generic_response"])
    @api.marshal_with(api.models["generic_response"], skip_none=True)
    def delete(self, iid):
        """
        Deletes all annotations from an image.
        """
        query = "DELETE FROM instance_seg_meta WHERE image_id = %s"
        try:
            db.query(query, (iid,))
        except DatabaseError as e:
            response = {
                "action": "failed",
                "error": {
                    "code": 500,
                    "message": e.msg
                }
            }
            code = 500
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
