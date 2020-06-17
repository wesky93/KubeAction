import logging

from flask import Flask, request

logging.basicConfig(level=logging.DEBUG)
app = Flask(__name__)


@app.route("/")
def hello():
    logging.info(f"{request}")
    logging.info(f"{request.data}")
    logging.info(f"{request.headers}")
    logging.info(f"{request.endpoint}")

    print(request)

    return "Hello from Python!"


if __name__ == "__main__":
    app.config['LOGGING_LEVEL'] = logging.DEBUG
    app.run(host='0.0.0.0')
