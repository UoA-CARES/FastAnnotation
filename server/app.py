from flask import Flask

from server.apis import api

app = Flask(__name__)
app.config['RESTPLUS_VALIDATE'] = True

api.init_app(app)
app.run(debug=True)
