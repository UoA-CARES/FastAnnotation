import base64
import os
from pathlib import Path
from shutil import copyfile, rmtree

import cv2
import numpy as np
from flask import request
from flask_restplus import Namespace, Resource, fields
from mysql.connector.errors import DatabaseError

from server.core.common_dtos import common_store
from server.server_config import DatabaseInstance
from server.server_config import ServerConfig

api = Namespace('projects', description='Project related operations')

db = DatabaseInstance()

api.models.update(common_store.get_dtos())

project = api.model('project', {
    'id': fields.Integer(attribute='project_id', required=False, description='The project identifier'),
    'name': fields.String(attribute='project_name', required=True, description='The project name'),
    'labeled_count': fields.Integer(required=False, description="The number of labeled images in the project"),
    'unlabeled_count': fields.Integer(required=False, description="The number of unlabeled images in the project"),
    'last_uploaded': fields.DateTime(required=False, description="The datetime when this project was last uploaded")
})

project_bulk = api.model('project_bulk', {
    'projects': fields.List(fields.Nested(project))
})

order_by = api.model('order_by', {
    'key': fields.String(
        required=False,
        default="id",
        enum=["id", "name"],
        description="The key on which to order"),
    'ascending': fields.Boolean(
        required=False,
        default=True,
        description="Indicates whether ascending or descending ordering should be used.")})

image_filter = api.model(
    'image_filter', {
        'locked': fields.Boolean(
            required=False,
            description="An optional flag for filtering locked images"),
        'labeled': fields.Boolean(
            required=False,
            description="An optional flag for filtering labeled images"),
        'order_by': fields.Nested(
            order_by,
            required=True,
            default={},
            description="An optional flag for ordering images")})

image_upload = api.model('image_upload', {
    'name': fields.String(required=True, description='The image name'),
    'ext': fields.String(required=True, description="The file extension of the image"),
    'image_data': fields.String(required=True, description="The encoded image data")
})

bulk_image_upload = api.model('bulk_image_upload', {
    'images': fields.List(fields.Nested(image_upload), required=True)
})


@api.route("")
class ProjectList(Resource):
    @api.response(200, "OK", project_bulk)
    @api.marshal_with(project_bulk, skip_none=True)
    def get(self):
        """
        Get a list of all available projects
        """
        results = db.query(
            "SELECT project_id, project_name, labeled_count, unlabeled_count, last_uploaded FROM project")[0]
        return {"projects": results}, 200

    @api.response(200, "Partial Success", api.models['bulk_response'])
    @api.response(201, "Success", api.models['bulk_response'])
    @api.marshal_with(api.models['bulk_response'], skip_none=True)
    @api.expect(project_bulk)
    def post(self):
        """
        A bulk operation for creating projects
        """
        content = request.json["projects"]

        code = 201
        bulk_response = []

        for row in content:
            query = "INSERT INTO project (project_name) "
            query += "VALUES (%s);"

            try:
                _, id = db.query(query, (row["name"],))
            except DatabaseError as e:
                result = {
                    "action": "failed",
                    "error": {
                        "code": 500,
                        "message": e.msg
                    }
                }
                bulk_response.append(result)
                code = 200
            except BaseException as e:
                result = {
                    "action": "failed",
                    "error": {
                        "code": 500,
                        "message": str(e)
                    }
                }
                bulk_response.append(result)
                code = 200
            else:
                result = {
                    "action": "created",
                    "id": id
                }
                bulk_response.append(result)

        return {"results": bulk_response}, code


@api.doc(params={"pid": "An id associated with an existing project."})
@api.route("/<int:pid>")
class Project(Resource):
    @api.response(200, "OK", project)
    @api.marshal_with(project, skip_none=True)
    def get(self, pid):
        """
        Get a project by its identifier.
        """
        query = "SELECT project_id, project_name, labeled_count, unlabeled_count, last_uploaded "
        query += "from project "
        query += "WHERE project_id = %s"
        results = db.query(query, (pid,))[0]
        return results, 200

    @api.response(200, "OK", api.models["generic_response"])
    @api.response(500, "Unexpected Failure", api.models["generic_response"])
    @api.marshal_with(api.models["generic_response"], skip_none=True)
    def delete(self, pid):
        """
        Delete a project by its identifier. All associated images and annotations will also be deleted.
        """
        q_delete_annotation = "DELETE FROM instance_seg_meta WHERE image_id IN"
        q_delete_annotation += " (SELECT image_id from image where project_fid = %s)"
        q_delete_images = "DELETE FROM image WHERE project_fid = %s"

        query = "DELETE FROM project WHERE project_id = %s"
        code = 200
        try:
            db.query(q_delete_annotation, (pid,))
            db.query(q_delete_images, (pid,))
            db.query(query, (pid,))
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
                "id": pid
            }
        return response, code


@api.doc(params={"pid": "An id associated with a project."})
@api.route("/<int:pid>/images")
class ProjectImageList(Resource):
    @api.response(200, "OK", api.models['generic_response'])
    @api.response(500, "Unexpected Failure", api.models['generic_response'])
    @api.marshal_with(api.models['generic_response'], skip_none=True)
    @api.expect(image_filter)
    def get(self, pid):
        """
        Get the images associated with the a project as referenced by its identifier.
        """
        content = request.json

        query = "SELECT image_id FROM fadb.image "
        query += "WHERE project_fid = %s"

        if "locked" in content:
            query += " and is_locked = " + str(content["locked"])

        if "labeled" in content:
            query += " and is_labeled = " + str(content["labeled"])

        valid_order_by = True
        if content["order_by"]["key"] == "id":
            query += " ORDER BY image_id"
        elif content["order_by"]["key"] == "name":
            query += " ORDER BY image_name"
        else:
            valid_order_by = False

        if valid_order_by:
            query += " asc" if content["order_by"]["ascending"] else " desc"

        code = 200
        try:
            results, _ = db.query(query, (pid,))
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
                "action": "read",
                "ids": [row['image_id'] for row in results]
            }
        return response, code

    @api.response(200, "Partial Success", api.models['bulk_response'])
    @api.response(201, "Success", api.models['bulk_response'])
    @api.expect(bulk_image_upload)
    @api.marshal_with(api.models['bulk_response'], skip_none=True)
    def post(self, pid):
        """
        A bulk operation for adding images to a project as referenced by its identifier.
        """
        content = request.json["images"]

        code = 201

        success_count = 0
        bulk_response = []
        for row in content:
            array = np.fromstring(
                base64.b64decode(
                    row["image_data"]),
                np.uint8)
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

            query = "INSERT INTO image (project_fid, image_path, image_name, image_ext) "
            query += "VALUES (%s, %s, %s, %s);"
            try:
                _, id = db.query(
                    query, (pid, img_path, row["name"], ServerConfig.DEFAULT_IMAGE_EXT))
                cv2.imwrite(img_path, img)
            except DatabaseError as e:
                response = {
                    "action": "failed",
                    "error": {
                        "code": 500,
                        "message": e.msg
                    }
                }
                code = 200
            except BaseException as e:
                response = {
                    "action": "failed",
                    "error": {
                        "code": 500,
                        "message": str(e)
                    }
                }
                code = 200
            else:
                response = {
                    "action": "created",
                    "id": id
                }
                success_count += 1
            bulk_response.append(response)

        # Increment unlabeled image count
        if success_count > 0:
            query = "UPDATE project SET unlabeled_count = unlabeled_count + %s WHERE project_id = %s"
            try:
                db.query(query, (success_count, pid))
            except DatabaseError as e:
                response = {
                    "action": "failed",
                    "error": {
                        "code": 500,
                        "message": e.msg
                    }
                }
                bulk_response.append(response)
                code = 200
        return {"results": bulk_response}, code

    @api.response(200, "OK", api.models['generic_response'])
    @api.response(500, "Unexpected Failure", api.models['generic_response'])
    @api.marshal_with(api.models['generic_response'], skip_none=True)
    def delete(self, pid):
        """
        Deletes all images associated with this project as referenced by its identifier.
        """

        q_get_image_ids = "SELECT image_id FROM image WHERE project_fid = %s"
        q_delete_annotations = "DELETE from instance_seg_meta WHERE image_id IN ("
        q_delete_annotations += q_get_image_ids
        q_delete_annotations += ")"
        query = "DELETE FROM image WHERE project_fid = %s"

        try:
            results, _ = db.query(q_get_image_ids, (pid,))
            db.query(q_delete_annotations, (pid,))
            db.query(query, (pid,))
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
                "ids": [x[0] for x in results]
            }
            code = 200

        return response, code


@api.doc(params={"pid": "An id associated with a project."})
@api.route("/<int:pid>/dataset")
class ProjectDataset(Resource):
    @api.response(200, "OK", api.models['generic_response'])
    @api.response(500, "Unexpected Failure", api.models['generic_response'])
    @api.marshal_with(api.models['generic_response'], skip_none=True)
    def get(self, pid):
        q_labelled_images = "SELECT image_id FROM fadb.image "
        q_labelled_images += "WHERE project_fid = %s"
        q_labelled_images += " and is_labeled = " + str(True)

        q_images = "SELECT image_id, image_path, image_name, image_ext FROM image "
        q_images += "WHERE image_id IN ("
        q_images += q_labelled_images
        q_images += ")"

        q_annotations = "SELECT image_id, annotation_id, annotation_name, mask_path, info_path FROM instance_seg_meta "
        q_annotations += "WHERE image_id IN ("
        q_annotations += q_labelled_images
        q_annotations += ")"

        rmtree(
            os.path.join(
                ServerConfig.DATA_ROOT_DIR,
                "export",
                str(pid)),
            ignore_errors=True)

        jpgs_folder = os.path.join(
            ServerConfig.DATA_ROOT_DIR,
            "export",
            str(pid),
            "jpgs")
        mask_folder = os.path.join(
            ServerConfig.DATA_ROOT_DIR,
            "export",
            str(pid),
            "trimaps")
        info_folder = os.path.join(
            ServerConfig.DATA_ROOT_DIR,
            "export",
            str(pid),
            "xmls")

        Path(jpgs_folder).mkdir(parents=True, exist_ok=True)
        Path(mask_folder).mkdir(parents=True, exist_ok=True)
        Path(info_folder).mkdir(parents=True, exist_ok=True)

        try:
            images, _ = db.query(q_images, (pid,))
            annotations, _ = db.query(q_annotations, (pid,))

            image_dict = {}
            annotation_count = {}

            for row in images:
                image_dict[row["image_id"]] = row["image_name"]
                annotation_count[row["image_name"]] = 0
                new_path = os.path.join(
                    jpgs_folder, row["image_name"] + row["image_ext"])
                copyfile(row["image_path"], new_path)

            for row in annotations:
                image_name = image_dict[row["image_id"]]
                annotation_count[image_name] += 1
                count = annotation_count[image_name]

                new_mask_path = os.path.join(
                    mask_folder, "%s_%04d%s" %
                    (image_name, count, ServerConfig.DEFAULT_MASK_EXT))
                new_info_path = os.path.join(
                    info_folder, "%s_%04d%s" %
                    (image_name, count, ServerConfig.DEFAULT_INFO_EXT))

                copyfile(row["mask_path"], new_mask_path)
                copyfile(row["info_path"], new_info_path)

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
                "action": "created"
            }
            code = 200

        return response, code
