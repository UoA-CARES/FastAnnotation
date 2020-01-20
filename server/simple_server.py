from flask import Flask
from flask import jsonify
from datetime import datetime

app = Flask(__name__)


@app.route("/")
def heartbeat():
    response = str(datetime.now())
    return jsonify(response)


if __name__ == "__main__":
    app.run()
