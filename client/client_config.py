import os
import configparser

from definitions import ROOT_DIR


class ClientConfig:
    """
    A collection of constants utilized by the client

    NOTE: All editable fields of this Config must be UPPERCASE to ensure correct loading from
    the config.ini file
    """

    # The section name which populates this config class
    CONFIG_FILE_SECTION = "CLIENT"

    SERVER_URL = ""

    SECONDS_PER_MINUTE = 60
    SECONDS_PER_HOUR = 3600
    SECONDS_PER_DAY = SECONDS_PER_HOUR * 24
    SECONDS_PER_MONTH = SECONDS_PER_DAY * 30
    SECONDS_PER_YEAR = SECONDS_PER_DAY * 365

    CLIENT_HIGHLIGHT_1 = "#3AD6E7"
    CLIENT_DARK_3 = "#0C273B"

    BBOX_SELECT = "#ff0000"
    BBOX_UNSELECT = "#ebcf1a"
    BBOX_THICKNESS = 1

    DATA_DIR = os.path.join(ROOT_DIR, 'client', 'data')

    CLIENT_POOL_LIMIT = 50

    EDITOR_MAX_DIM = None
    TILE_MAX_DIM = 150

    REFIT_IMAGES = False

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
