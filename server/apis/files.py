import io
import os
import zipfile

from flask import send_file
from flask_restplus import Namespace, Resource
from flask import request

from mysql.connector.errors import DatabaseError

from server.core.common_dtos import common_store
from server.server_config import DatabaseInstance
from server.server_config import ServerConfig

import server.utils as utils

import cv2
import numpy as np
import json

from pathlib import Path

api = Namespace('files', description='File serving')

db = DatabaseInstance()

api.models.update(common_store.get_dtos())

from werkzeug.datastructures import FileStorage
from flask_restplus import reqparse

file_upload = reqparse.RequestParser()
file_upload.add_argument('File Upload',
                         type=FileStorage,
                         location='files',
                         required=True,
                         help='File Upload')


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


@api.route("/image/<int:iid>/annotations")
class AnnotationDownload(Resource):
    @api.response(200, "OK")
    @api.response(400, "Database Failure", api.models["generic_response"])
    @api.response(404, "Image not found", api.models["generic_response"])
    @api.response(500, "Unexpected Failure", api.models["generic_response"])
    def get(self, iid):
        """
        A file serving operation for retrieving all annotations associated with an image.
        """

        query = "SELECT annotation_id, mask_path, info_path FROM instance_seg_meta WHERE image_id  = %s"
        try:
            result, _ = db.query(query, (iid,))

            if not result:
                response = {
                    "action": "failed",
                    "error": {
                        "code": 404,
                        "message": "Image with id %s, does not exist." % iid
                    }
                }
                return response, 404

            data = io.BytesIO()
            with zipfile.ZipFile(data, mode='w') as z:
                for row in result:
                    _, ext = os.path.splitext(os.path.basename(row['mask_path']))
                    z.write(row['mask_path'], str(row["annotation_id"]) + ext)
            data.seek(0)

            return send_file(
                data,
                mimetype='application/zip',
                as_attachment=True,
                attachment_filename='data.zip'
            )
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

    @api.marshal_with(api.models["generic_response"], skip_none=True)
    @api.expect(file_upload)
    def post(self, iid):
        file_bytes = request.files['file'].read()
        info_bytes = request.files['info'].read()
        info = json.loads(info_bytes.decode('utf-8'))
        zf = zipfile.ZipFile(io.BytesIO(file_bytes), "r")

        code = 201
        new_rows = []
        for row in info["annotations"]:
            mask_path = os.path.join(
                ServerConfig.DATA_ROOT_DIR,
                "annotation",
                str(iid),
                "trimaps",
                "%s.png" % row["name"])
            info_path = os.path.join(
                ServerConfig.DATA_ROOT_DIR,
                "annotation",
                str(iid),
                "xmls",
                "%s.xml" % row["name"])

            new_rows.append((row['name'], iid, mask_path, info_path, row["class_name"]))

            folder = os.path.dirname(mask_path)
            Path(folder).mkdir(parents=True, exist_ok=True)
            cv2.imwrite(mask_path, utils.bytes2mat(zf.read(row['name'] + ".jpg")))

            utils.save_info(
                shape=row["shape"],
                bbox=row["bbox"],
                class_name=row["class_name"],
                filepath=info_path)

        q_delete_old = "DELETE FROM instance_seg_meta WHERE image_id = %s"
        q_replace = "REPLACE INTO instance_seg_meta (annotation_name, image_id, mask_path, info_path, class_name)"
        try:
            db.query(q_delete_old, (iid,))
            q_replace += "\nVALUES "
            q_replace += ",".join(["(%s,%s,%s,%s,%s)"] * len(new_rows))
            params = tuple(sum(new_rows, ()))
            _, ids = db.query(q_replace, params)
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
                "action": "created"
            }
        return response, code

