import os

from database.database import Database
from definitions import ROOT_DIR


class ServerConfig:
    DATABASE_HOST = "127.0.0.1"
    DATABASE_USER = "root"
    DATABASE_PASSWORD = "root"
    DATABASE_NAME = "fadb"
    DATABASE_POOL_SIZE = 3
    DATABASE_TIMEZONE = '+00:00'

    DATA_ROOT_DIR = os.path.join(ROOT_DIR, "database", "DATA")
    DEFAULT_IMAGE_EXT = ".jpg"

    # Used to white list filter combinations for Project Images
    IMAGE_FILTER_MAP = {
        "locked": {
            True: "is_locked = 1",
            False: "is_locked = 0"
        },
        "labelled": {
            True: "is_labelled = 1",
            False: "is_labelled = 0"
        }
    }

    IMAGE_ORDER_BY_MAP = {
        "name": "image_name",
        "id": "image_id"
    }


class DatabaseInstance:
    __instance = None

    def __new__(cls):
        if DatabaseInstance.__instance is None:
            DatabaseInstance.__instance = Database(ServerConfig())
        return DatabaseInstance.__instance
