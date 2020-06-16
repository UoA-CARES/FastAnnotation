import uuid

from sqlalchemy.dialects.postgresql import UUID


from server import db


def uuid_primary_key_column():
    return db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)


def uuid_type():
    return UUID(as_uuid=True)