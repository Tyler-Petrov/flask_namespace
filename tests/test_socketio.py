from flask import Flask
from flask_socketio import SocketIO

from flask_namespace.socketio import SocketIONamespace


def test_socketio():
    app = Flask(__name__)
    socketio = SocketIO(app)

    class TestSocket(SocketIONamespace):
        pass

    TestSocket.register_namespace(socketio)

    assert TestSocket.url_prefix == "/Test", "Namespace url not set properly"


test_socketio()
