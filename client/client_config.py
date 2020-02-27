import os

from definitions import ROOT_DIR


class ClientConfig:
    """ A collection of constants utilized by the client """

    SERVER_URL = "http://localhost:5000/"

    SECONDS_PER_MINUTE = 60
    SECONDS_PER_HOUR = 3600
    SECONDS_PER_DAY = SECONDS_PER_HOUR * 24
    SECONDS_PER_MONTH = SECONDS_PER_DAY * 30
    SECONDS_PER_YEAR = SECONDS_PER_DAY * 365

    CLIENT_HIGHLIGHT_1 = "3AD6E7"

    SCREEN_DIR = os.path.join(ROOT_DIR, 'client', 'screens')
