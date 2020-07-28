import pathlib
import os
from flask import Flask

from server.server_config import ServerConfig

CONFIG_PATH = os.path.join(pathlib.Path(__file__).parent.absolute(), 'config.ini')
ServerConfig.load_config(CONFIG_PATH)

if __name__ == "__main__":
    from server.apis import api

    app = Flask(__name__)
    app.config['RESTPLUS_VALIDATE'] = True
    app.config['RESTPLUS_MASK_SWAGGER'] = False

    api.init_app(app)
    app.run(debug=True, port="5001")
