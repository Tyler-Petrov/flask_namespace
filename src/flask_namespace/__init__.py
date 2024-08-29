from flask import Flask, g
from flask_socketio import SocketIO
from werkzeug.local import LocalProxy


def _lookup_nsp():
    try:
        return g._route_namespace
    except AttributeError:
        raise RuntimeError(
            """\
Tried to access the global nsp outside of a flask_namespace route. The variable nsp is only available inside a route from flask namespace\
"""
        )


nsp = LocalProxy(_lookup_nsp)


class Namespace:
    def __init__(self, app: Flask, socketio: SocketIO | None = None):
        self.app_context = app

        if socketio is None:
            socketio = SocketIO(app)
        self.socketio_context = socketio

        app.jinja_env.globals["nsp"] = nsp

    def register_namespace(self, namespace_class: "RouteNamespace | SocketIONamespace"):
        if isinstance(namespace_class, RouteNamespace):
            namespace_class.register_route_namespace(self.app_context)
        if isinstance(namespace_class, SocketIONamespace):
            return namespace_class.register_socketio_namespace(self.socketio_context)


from .route import RouteNamespace
from .socketio import SocketIONamespace
