import os

from definitions import ROOT_DIR


class ClientConfig:
    """
    A collection of constants utilized by the client

    NOTE: All editable fields of this Config must be UPPERCASE to ensure correct loading from
    the config.ini file
    """

    # The section name which populates this config class
    CONFIG_FILE_SECTION = "CLIENT"

    SERVER_URL = "http://localhost:5001/"

    SECONDS_PER_MINUTE = 60
    SECONDS_PER_HOUR = 3600
    SECONDS_PER_DAY = SECONDS_PER_HOUR * 24
    SECONDS_PER_MONTH = SECONDS_PER_DAY * 30
    SECONDS_PER_YEAR = SECONDS_PER_DAY * 365

    CLIENT_HIGHLIGHT_1 = "#3AD6E7"
    CLIENT_DARK_3 = "#0C273B"

    BBOX_SELECT = "#ff0000"
    BBOX_UNSELECT = "#ebcf1a"

    DATA_DIR = os.path.join(ROOT_DIR, 'client', 'data')

    CLIENT_POOL_LIMIT = 50

    EDITOR_MAX_DIM = None
    TILE_MAX_DIM = 150
