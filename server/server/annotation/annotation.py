from flask import abort
from flask_restful import reqparse, Resource, fields, marshal_with
from sqlalchemy.dialects.postgresql import JSON
from flask_restful_swagger import swagger


from server import api, db
from server.pagination import get_pagination_args

"""
Notes: 
Annotations themselves don't know if they are from a human or machine. This information is stored at the image level.
If we were to store this information at the Annotation level as well then we would need to introduce consistency checks.
"""


class Annotation(db.Model):
    __tablename__ = 'annotations'

    id = db.Column(db.Integer, primary_key=True)
    coco = db.Column(JSON, nullable=False)

    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    image_id = db.Column(db.Integer, db.ForeignKey('images.id'), nullable=False)


def get_annotation_args_parser():
    args_parser = reqparse.RequestParser()
    args_parser.add_argument('coco', type=dict, required=True)
    return args_parser


@swagger.model
class AnnotationModel:

    resource_fields = {
        'id': fields.Integer,
        'coco': fields.Raw
    }


@swagger.model
class PostAnnotationModel:
    def __init__(self, coco):
        pass


@swagger.model
class PutAnnotationModel:
    resource_fields = {
        "coco": fields.Raw,
    }


def get_annotation_or_404(project_id: int, image_id: int, annotation_id: int):
    annotation = Annotation.query.filter_by(id=annotation_id, project_id=project_id, image_id=image_id).first()
    if annotation is None:
        abort(404, "Annotation not found")
    return annotation


class Annotations(Resource):
    @swagger.operation(
        responseClass=AnnotationModel.__name__,
    )
    @marshal_with(AnnotationModel.resource_fields)
    def get(self, project_id, image_id, annotation_id):
        annotation = get_annotation_or_404(project_id=project_id, image_id=image_id, annotation_id=annotation_id)
        return annotation, 200

    @swagger.operation(
        responseClass=AnnotationModel.__name__,
        parameters=[{
            "name": "body",
            "dataType": PutAnnotationModel.__name__,
            "required": True
        }]
    )
    @marshal_with(AnnotationModel.resource_fields)
    def put(self, project_id: int, image_id: int, annotation_id: int):
        args = get_annotation_args_parser().parse_args()
        annotation = get_annotation_or_404(project_id=project_id, image_id=image_id, annotation_id=annotation_id)
        annotation.coco = args.coco
        db.session.commit()
        db.session.refresh(annotation)
        return annotation, 200

    # TODO Delete verb


class AnnotationList(Resource):
    @swagger.operation(
        responseClass=AnnotationModel.__name__,
    )
    @marshal_with(AnnotationModel.resource_fields)
    def post(self, project_id: int, image_id: str):
        args = get_annotation_args_parser().parse_args()
        annotation = Annotation(**args, project_id=project_id, image_id=image_id)
        db.session.add(annotation)
        db.session.commit()
        db.session.refresh(annotation)
        return annotation, 201


api.add_resource(AnnotationList, '/projects/<int:project_id>/images/<int:image_id>/annotations')
api.add_resource(Annotations, '/projects/<int:project_id>/images/<int:image_id>/annotations/<int:annotation_id>')