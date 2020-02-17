import os

from definitions import ROOT_DIR
from database.database import Database


class ServerConfig:
    DATABASE_HOST = "127.0.0.1"
    DATABASE_USER = "root"
    DATABASE_PASSWORD = "root"
    DATABASE_NAME = "fadb"
    DATABASE_POOL_SIZE = 5
    DATABASE_TIMEZONE = '+00:00'

    DATA_ROOT_DIR = os.path.join(ROOT_DIR, "database", "DATA")


class DatabaseInstance:
    __instance = None

    def __new__(cls):
        if DatabaseInstance.__instance is None:
            DatabaseInstance.__instance = Database(ServerConfig())
        return DatabaseInstance.__instance
