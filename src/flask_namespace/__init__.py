import inspect
import re
from typing import Callable

from flask import Blueprint, Flask, g, render_template
from itsdangerous import URLSafeTimedSerializer

from flask_namespace.exceptions import OutsideLocality


class Signer(URLSafeTimedSerializer):
    @classmethod
    def find_closest_route_namespace(cls):

        # Traverse the call stack and find BaseBlueprintNamespace
        for frame_info in inspect.stack():
            frame = frame_info.frame

            # Get the 'self' from the frame locals
            instance = frame.f_locals.get("self") or frame.f_locals.get("cls")

            if not (instance and isinstance(instance, Namespace)):
                continue

            return instance

    @classmethod
    def locality(cls, local: bool | type | str = True) -> str | None:
        if local is False:
            return None

        if isinstance(local, type):
            return local.__name__

        if isinstance(local, str):
            return local

        if namespace_cls := cls.find_closest_route_namespace():
            return namespace_cls.__name__

        return None

    def dumps(
        self,
        obj,
        salt: str | bytes | None = None,
        local: bool | type | str = True,
    ) -> str | bytes:

        # Wrap data in dictionary so configuration can be stored
        data = {"data": obj, "locality": self.locality(local)}

        return super().dumps(data, salt)

    def loads(
        self,
        s: str | bytes,
        max_age: int | None = None,
        return_timestamp: bool = False,
        salt: str | bytes | None = None,
        local: bool | type | str = True,
    ):
        parsed_data = super().loads(
            s,
            max_age=max_age,
            return_timestamp=return_timestamp,
            salt=salt,
        )

        if (locality := parsed_data.get("locality")) and locality != (
            current_locality := self.locality(local)
        ):
            raise OutsideLocality(
                f"Itsdangerous data attempted to be parsed outside of set locality. Previous locality: {locality}, Current locality: {current_locality}"
            )

        return parsed_data.get("data") or parsed_data


class ClassMethodsMeta(type):
    def __instancecheck__(self, instance):
        try:
            return self in instance.mro()
        except:
            return super().__instancecheck__(instance)

    def __new__(cls, name, bases, dct):
        # Iterate over the class dictionary
        for attr_name, attr_value in dct.items():
            if callable(attr_value) and not attr_name.startswith("__"):
                dct[attr_name] = classmethod(attr_value)
        return super().__new__(cls, name, bases, dct)


class Namespace(metaclass=ClassMethodsMeta):
    @staticmethod
    def route_prefix_to_http_method(route_method_name):
        split_name = route_method_name.split("_")
        route_prefix, route_endpoint = split_name[0], "_".join(split_name[1:])
        conversion_key = {"get": ["GET"], "post": ["POST"], "form": ["GET", "POST"]}
        return route_prefix, route_endpoint, conversion_key.get(route_prefix)

    def prepare_endpoint(cls, endpoint_func: Callable):
        return endpoint_func

    def register_namespace(cls, app: Flask):
        if not hasattr(cls, "url_prefix"):
            class_name_prefix = cls.__name__.replace("Routes", "")
            cls.url_prefix = f"/{class_name_prefix}"

        if not hasattr(cls, "namespace_name"):
            cls.namespace_name = cap_to_snake_case(cls.url_prefix.replace("/", ""))

        cls.blueprint = Blueprint(
            cls.namespace_name, __name__, url_prefix=cls.url_prefix
        )

        for attr_name in dir(cls):
            # Get the prefix, and the corresponding http methods
            route_prefix, route_endpoint, http_methods = (
                cls.route_prefix_to_http_method(attr_name)
            )

            # If the attribute name isn't matched as a route
            if not http_methods:
                continue

            # Get the method from the class by the attribute name
            route_method = getattr(cls, attr_name)

            # Get the non cls parameters from the route's method in list<str> format
            url_params = [
                str(param)
                for param in inspect.signature(route_method).parameters.values()
            ]

            # Join the remaining method params with a trailing /
            url_param_str = "".join([f"/<{param}>" for param in url_params])

            # Replace the underscores with dashes for the url
            route_url_suffix = route_endpoint.replace("_", "-")

            prepared_endpoint = cls.prepare_endpoint(route_method)

            # Save the route to the blueprint
            cls.blueprint.route(
                f"{url_param_str}/{route_url_suffix}",
                methods=http_methods,
                endpoint=route_endpoint,
            )(prepared_endpoint)

        # Register the blueprint to the flask app
        app.register_blueprint(cls.blueprint)

    def render_template(cls, template_name_or_list: str | list, **context) -> str:
        g.template_name = template_name_or_list
        g.namespace = cls

        return render_template(
            template_name_or_list,
            **context,
        )
