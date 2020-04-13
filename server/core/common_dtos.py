from flask_restplus import fields, Model
from server.core.dto_store import DtoStore

common_store = DtoStore()

error_model = Model('error_response', {
    'code': fields.Integer(
        required=False,
        description="An optional error code associated with the failure"),
    'message': fields.String})
common_store.add_dto(error_model)

generic_model = Model('generic_response', {
    'action': fields.String(
        required=True,
        description="The action performed on the bulk item",
        enum=["created", "read", "updated", "deleted", "failed"]),
    'error': fields.Nested(
        error_model,
        required=False,
        skip_none=True,
        description="An optional error message"),
    'id': fields.Integer(
        required=False,
        description="An optional identifier"),
    'ids': fields.List(
        fields.Integer,
        required=False,
        description="An optional list of identifiers")
})

common_store.add_dto(generic_model)

common_store.add_dto(Model('bulk_response', {
    'results': fields.List(fields.Nested(generic_model, skip_none=True))
}))
