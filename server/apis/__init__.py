from flask_restplus import Api

from .project import api as project_api
from .image import api as image_api
from .files import api as files_api

api = Api(
    title='FastAnnotation API',
    version='1.0',
    description='The annotation handling API for the FastAnnotation tool.',
)

api.add_namespace(project_api)
api.add_namespace(image_api)
api.add_namespace(files_api)