import os
import configparser

from database.database import Database
from definitions import ROOT_DIR


class ServerConfig:
    CONFIG_FILE_SECTION = "SERVER"
    DATABASE_HOST = "localhost"
    DATABASE_USER = ""
    DATABASE_PASSWORD = ""
    DATABASE_NAME = ""
    DATABASE_TIMEZONE = '+00:00'
    DATABASE_POOL_SIZE = 3

    DATA_ROOT_DIR = os.path.join(ROOT_DIR, "database", "DATA")
    XML_TEMPLATE_PATH = os.path.join(ROOT_DIR, "server", "data", "template.xml")
    DEFAULT_IMAGE_EXT = ".jpg"
    DEFAULT_MASK_EXT = ".png"
    DEFAULT_INFO_EXT = ".xml"

    @classmethod
    def load_config(cls, path):
        def get_best_type(section, key):
            output = section.get(key)
            try:
                output = section.getboolean(key)
            except ValueError:
                pass

            try:
                output = section.getfloat(key)
            except ValueError:
                pass

            try:
                output = section.getint(key)
            except ValueError:
                pass

            return output

        config = configparser.ConfigParser()
        config.read(path)
        try:
            for k in config[cls.CONFIG_FILE_SECTION]:
                try:
                    setattr(cls, k.upper(), get_best_type(config[cls.CONFIG_FILE_SECTION], k))
                except AttributeError:
                    continue
        except KeyError:
            pass


class DatabaseInstance:
    __instance = None

    def __new__(cls):
        if DatabaseInstance.__instance is None:
            DatabaseInstance.__instance = Database(ServerConfig())
        return DatabaseInstance.__instance
