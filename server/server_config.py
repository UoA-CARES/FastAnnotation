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
    XML_TEMPLATE_PATH = os.path.join(ROOT_DIR, "server", "template.xml")
    DEFAULT_IMAGE_EXT = ".jpg"
    DEFAULT_MASK_EXT = ".png"
    DEFAULT_INFO_EXT = ".xml"


class DatabaseInstance:
    __instance = None

    def __new__(cls):
        if DatabaseInstance.__instance is None:
            DatabaseInstance.__instance = Database(ServerConfig())
        return DatabaseInstance.__instance
