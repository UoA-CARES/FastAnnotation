import pkg_resources
import pathlib
import os
from flask import Flask
import sys
from server.server_config import ServerConfig

if __name__ == "__main__":
    CONFIG_PATH = os.path.join(pathlib.Path(sys.argv[0]).parent.absolute(), 'config.ini')
    ServerConfig.load_config(CONFIG_PATH)

    from server.apis import api
    app = Flask(__name__)
    app.config['RESTPLUS_VALIDATE'] = True
    app.config['RESTPLUS_MASK_SWAGGER'] = False

    api.init_app(app)
    app.run(debug=True, port="5001")
