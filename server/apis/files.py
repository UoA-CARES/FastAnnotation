from flask import send_file
from flask_restplus import Namespace, Resource
from mysql.connector.errors import DatabaseError

from server.core.common_dtos import common_store
from server.server_config import DatabaseInstance

api = Namespace('files', description='File serving')

db = DatabaseInstance()

api.models.update(common_store.get_dtos())


@api.route("/image/<int:iid>")
class ImageDownload(Resource):
    @api.response(200, "OK")
    @api.response(400, "Database Failure", api.models["generic_response"])
    @api.response(404, "Image not found", api.models["generic_response"])
    @api.response(500, "Unexpected Failure", api.models["generic_response"])
    def get(self, iid):
        """
        A file serving operation for retrieving images by id.
        """

        query = "SELECT image_path FROM image WHERE image_id  = %s"
        try:
            result, _ = db.query(query, (iid,))
        except DatabaseError as e:
            response = {
                "action": "failed",
                "error": {
                    "code": 400,
                    "message": e.msg
                }
            }
            return response, 400
        except BaseException as e:
            response = {
                "action": "failed",
                "error": {
                    "code": 500,
                    "message": str(e)
                }
            }
            return response, 500
        else:
            if not result:
                response = {
                    "action": "failed",
                    "error": {
                        "code": 404,
                        "message": "Image with id %s, does not exist." % iid
                    }
                }
                return response, 404

            path = result[0]["image_path"]
            return send_file(path)


@api.route("/annotation/<int:aid>")
class AnnotationDownload(Resource):
    @api.response(200, "OK")
    @api.response(400, "Database Failure", api.models["generic_response"])
    @api.response(404, "Image not found", api.models["generic_response"])
    @api.response(500, "Unexpected Failure", api.models["generic_response"])
    def get(self, aid):
        """
        A file serving operation for retrieving annotations by id.
        """

        query = "SELECT image_path FROM instance_seg_meta WHERE annotation_id  = %s"
        try:
            result, _ = db.query(query, (aid,))
        except DatabaseError as e:
            response = {
                "action": "failed",
                "error": {
                    "code": 400,
                    "message": e.msg
                }
            }
            return response, 400
        except BaseException as e:
            response = {
                "action": "failed",
                "error": {
                    "code": 500,
                    "message": str(e)
                }
            }
            return response, 500
        else:
            if not result:
                response = {
                    "action": "failed",
                    "error": {
                        "code": 404,
                        "message": "Image with id %s, does not exist." % aid
                    }
                }
                return response, 404

            path = result[0]["image_path"]
            return send_file(path)
