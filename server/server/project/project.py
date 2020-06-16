from flask_restful import reqparse, Resource, fields, marshal_with


from server import api, db
from server.pagination import get_pagination_args
from flask_restful_swagger import swagger


class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text)
    images = db.relationship('Image', backref='project', lazy=True)


def get_project_args_parser():
    project_args_parser = reqparse.RequestParser()
    project_args_parser.add_argument('name', type=str, required=True)
    project_args_parser.add_argument('description', type=str, required=False)
    return project_args_parser


@swagger.model
class ProjectModel:

    resource_fields = {
        'id': fields.Integer,
        'name': fields.String,
        'description': fields.String
    }


@swagger.model
class PostProjectModel:
    def __init__(self, name, description):
        pass


@swagger.model
class PutProjectModel:
    resource_fields = {
        "name": fields.String,
        "description": fields.String
    }


class Projects(Resource):
    @swagger.operation(
        responseClass=ProjectModel.__name__,
    )
    @marshal_with(ProjectModel.resource_fields)
    def get(self, project_id):
        return Project.query.get_or_404(project_id)

    # TODO delete verb. Will need to delete relations as well.
    @swagger.operation(
        responseClass=ProjectModel.__name__,
        parameters=[{
            "name": "body",
            "dataType": PutProjectModel.__name__,
            "required": True
        }]
    )
    @marshal_with(ProjectModel.resource_fields)
    def put(self, project_id: int):
        args = get_project_args_parser().parse_args()
        project = Project.query.get_or_404(project_id)
        project.name = args.name
        project.description = args.description
        db.session.commit()
        db.session.refresh(project)
        return project, 200


api.add_resource(Projects, '/projects/<int:project_id>')


class ProjectList(Resource):
    # TODO update swagger docs to include pagination args.
    @swagger.operation(
        responseClass=ProjectModel.__name__,
    )
    @marshal_with(ProjectModel.resource_fields)
    def get(self):
        args = get_pagination_args()
        return Project.query.paginate(args.page_number, args.results_per_page).items

    @swagger.operation(
        responseClass=ProjectModel.__name__,
        parameters=[{
            "name": "body",
            "dataType": PostProjectModel.__name__,
            "required": True
        }]
    )
    @marshal_with(ProjectModel.resource_fields)
    def post(self):
        args = get_project_args_parser().parse_args()
        project = Project(**args)
        db.session.add(project)
        db.session.commit()
        db.session.refresh(project)
        return project, 201


api.add_resource(ProjectList, '/projects')

