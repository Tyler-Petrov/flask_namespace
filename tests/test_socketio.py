from flask import Flask
from flask_socketio import SocketIO

from flask_namespace import Namespace
from flask_namespace.socketio import SocketIONamespace


def test_socketio():
    app = Flask(__name__)
    namespace = Namespace(app)

    class TestSocket(SocketIONamespace):
        pass

    namespace.register_namespace(TestSocket)

    assert TestSocket.url_prefix == "/Test", "Namespace url not set properly"


test_socketio()
