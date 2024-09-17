from functools import wraps
from typing import Optional

from flask import request
from flask_socketio import Namespace as Namespace_
from flask_socketio import SocketIO

from .helpers import NamespaceBase


class InvalidRoom(Exception):
    pass


class Connection:
    def __init__(self, sid, **kwargs) -> None:
        self.sid = sid
        for key, value in kwargs.items():
            setattr(self, key, value)


class Room:
    def __init__(self, name, namespace: "SocketIONamespace") -> None:
        self.name = name
        self.namespace = namespace
        self.connections = {}

    def __len__(self):
        return len(self.connections)

    @property
    def connection_count(self):
        return len(self)

    def add_current_connection(self):
        self.add_connection(
            sid=request.sid,
            connection=Connection(request.sid),
        )

    def add_connection(self, sid, connection):
        self.connections[sid] = connection

    def remove_connection(self, sid):
        del self.connections[sid]


class NamespaceMeta(type):
    @staticmethod
    def event_wrapper(f: "function"):
        """This method wraps every SocketIO event method

        Args:
            f (function): SocketIO event method

        Returns:
            function: Wrapped SocketIO event method
        """

        @wraps(f)
        def event_function(self: "SocketIONamespace", data=None, *args, **kwargs):
            if data is None:
                data = {}

            if not isinstance(data, dict):
                raise TypeError("Event data passed must be a dictionary")

            data, args, kwargs = self.before_event(data, args, kwargs)

            try:
                self.current_room = data.pop("room_name")
            except KeyError:
                self.current_room = None

            self.current_event = f.__name__.replace("on_", "", 1)

            if (
                self.current_event != "join_room"
                and self.current_room is not None
                and not self.authorize_connection_in_current_room()
            ):
                raise InvalidRoom(
                    "Blocked incoming event: Connection sending to a room they aren't in"
                )

            return f(self, *args, **kwargs, **data)

        return event_function

    def __instancecheck__(self, instance):
        try:
            return self in instance.mro()
        except:
            return super().__instancecheck__(instance)

    def __new__(cls, name, bases, dct):
        # Iterate over the class dictionary
        for attr_name, attr_value in dct.items():
            # Don't loop over non methods or dunder methods
            if not callable(attr_value) or attr_name.startswith("__"):
                continue

            # If method isn't an event method then don't loop over it
            if not attr_name.startswith("on_"):
                continue

            # Wrap every event method with wrapper
            dct[attr_name] = cls.event_wrapper(attr_value)
        return super().__new__(cls, name, bases, dct)


class SocketIONamespace(NamespaceBase, Namespace_, metaclass=NamespaceMeta):
    class_definition_suffix = "Socket"

    rooms_: dict[str, Room]
    current_room: Optional[str] = None
    current_event: Optional[str] = None

    def __init__(self, namespace=None):
        # Must set mutable dict in the init function, so it's not globalized
        self.rooms_ = {}
        return super().__init__(namespace=namespace)

    def emit(
        self,
        event,
        data=None,
        room=None,
        include_self=True,
        namespace=None,
        callback=None,
    ):
        return super().emit(
            event,
            data,
            room=room,
            include_self=include_self,
            namespace=namespace or self.namespace,
            callback=callback,
        )

    def join_room_rejection(self):
        return

    def get_room_obj(self, room_name) -> Room:
        if not self.rooms_.get(room_name):
            self.rooms_[room_name] = Room(room_name, self)
        return self.rooms_[room_name]

    def enter_room(self, sid, room_name, namespace=None):
        connection_allowed = self.authorize_room_join(room_name)
        if not connection_allowed:
            return False

        super().enter_room(sid, room_name, namespace or self.namespace)

        # Add current collection to the current room
        room = self.get_room_obj(room_name)
        room.add_current_connection()

        return True

    def authorize_room_join(self, room_name) -> bool:
        return True

    def authorize_event(self, event_name, room_name) -> bool:
        return True

    def authorize_connection_in_room(self, room_name: str, sid=None):
        if sid is None:
            sid = request.sid
        return room_name in self.rooms(sid)

    def authorize_connection_in_current_room(self):
        return self.authorize_connection_in_room(self.current_room, request.sid)

    def before_event(self, event_data, event_args, event_kwargs):
        return event_data, event_args, event_kwargs

    def emit_global_event(self, event_name, room, kwargs):
        self.emit(
            "global_event",
            {"event_name": event_name, **kwargs},
            namespace=self.namespace,
            room=room,
        )

    def on_disconnect(self):
        for room in self.rooms(request.sid):
            if room not in self.rooms_:
                continue
            self.rooms_[room].remove_connection(request.sid)

    def on_rooms(self):
        for _, room in self.rooms_.items():
            print(room.name, room.connection_count)
            for _, connection in room.connections.items():
                print(" - ", connection.sid)

    def on_join_room(self):
        joined_room = self.enter_room(request.sid, room_name=self.current_room)

        self.emit(
            self.current_event,
            {"joined_room": joined_room, "sid": request.sid},
            namespace=self.namespace,
            room=request.sid,
        )

    def on_trigger_global_event(self, room, **kwargs):
        self.emit_global_event(room, kwargs)

    @classmethod
    def register_socketio_namespace(cls, socketio_instance: SocketIO):
        namespace = cls(
            namespace=cls.url_prefix,
        )
        socketio_instance.on_namespace(namespace)
        return namespace
