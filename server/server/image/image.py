from flask import abort
from flask_restful import reqparse, Resource, fields, marshal_with

from server import api, db
from server.pagination import get_pagination_args
from flask_restful_swagger import swagger


class Image(db.Model):
    __tablename__ = 'images'

    id = db.Column(db.Integer, primary_key=True)
    path = db.Column(db.String(80), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    human_annotation = db.relationship('Annotation', backref='image', lazy=True)


def get_image_args_parser():
    args_parser = reqparse.RequestParser()
    args_parser.add_argument('path', type=str, required=True)
    return args_parser


def get_image_fields():
    return {
        'id': fields.Integer,
        'path': fields.String,
    }


def get_image_or_404(project_id: int, image_id: int):
    image = Image.query.filter_by(id=image_id, project_id=project_id).first()
    if image is None:
        abort(404, "Image not found")
    return image


@swagger.model
class ImageModel:

    resource_fields = {
        'id': fields.Integer,
        'path': fields.String
    }


@swagger.model
class PostImageModel:
    def __init__(self, path):
        pass


@swagger.model
class PutImageModel:
    resource_fields = {
        "path": fields.String,
    }


class Images(Resource):
    @swagger.operation(
        responseClass=ImageModel.__name__,
    )
    @marshal_with(ImageModel.resource_fields)
    def get(self, project_id, image_id):
        image = get_image_or_404(project_id=project_id, image_id=image_id)
        return image, 200

    @swagger.operation(
        responseClass=ImageModel.__name__,
        parameters=[{
            "name": "body",
            "dataType": PutImageModel.__name__,
            "required": True
        }]
    )
    @marshal_with(ImageModel.resource_fields)
    def put(self, project_id, image_id):
        args = get_image_args_parser().parse_args()
        image = get_image_or_404(project_id=project_id, image_id=image_id)
        image.path = args.path
        # Don't allow the project_id of an image to be updated. This enforces project-level isolation of images.
        db.session.commit()
        db.session.refresh(image)
        return image, 200

    # TODO Delete verb


class ImageList(Resource):

    @swagger.operation(
        responseClass=ImageModel.__name__,
    )
    @marshal_with(ImageModel.resource_fields)
    def get(self):
        args = get_pagination_args()
        return Image.query.paginate(args.page_number, args.results_per_page).items

    @swagger.operation(
        responseClass=ImageModel.__name__,
        parameters=[{
            "name": "body",
            "dataType": PutImageModel.__name__,
            "required": True
        }]
    )
    @marshal_with(ImageModel.resource_fields)
    def post(self, project_id):
        args = get_image_args_parser().parse_args()
        image = Image(**args, project_id=project_id)
        db.session.add(image)
        db.session.commit()
        db.session.refresh(image)
        return image, 201


api.add_resource(ImageList, '/projects/<int:project_id>/images')
api.add_resource(Images, '/projects/<int:project_id>/images/<int:image_id>')
