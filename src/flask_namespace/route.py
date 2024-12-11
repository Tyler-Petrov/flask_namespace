import inspect
from functools import wraps
from typing import Callable, Optional

from flask import Blueprint, Flask, g, render_template, request
from markupsafe import Markup

from .helpers import ClassMethodsMeta, Endpoint, NamespaceBase


class RouteNamespace(NamespaceBase, metaclass=ClassMethodsMeta):
    _endpoints: list[Endpoint]
    class_definition_suffix = "Routes"
    template_file_ext = "jinja"

    def prepare_endpoint(cls, endpoint_func: Callable):
        return endpoint_func

    def before_request(cls):
        g._route_namespace = cls

    def before_request_wrapper(cls, f):
        @wraps(f)
        def wrapper_function(*args, **kwargs):
            cls.before_request()
            return f(*args, **kwargs)

        return wrapper_function

    def format_endpoint_name(cls, endpoint_name: str) -> str:
        return endpoint_name

    def register_route_namespace(cls, app: Flask):
        cls.blueprint = Blueprint(
            cls.namespace_name, __name__, url_prefix=cls.url_prefix
        )

        for endpoint in cls._endpoints:
            # Call modifier class methods
            wrapped_endpoint = cls._default_endpoint_response(endpoint)
            prepared_endpoint = cls.prepare_endpoint(
                cls.before_request_wrapper(wrapped_endpoint)
            )

            # Save the route to the blueprint
            cls.blueprint.route(
                endpoint.url,
                methods=endpoint.http_methods,
                endpoint=endpoint.endpoint_name,
            )(prepared_endpoint)

        # Register the blueprint to the flask app
        app.register_blueprint(cls.blueprint)

    def _default_endpoint_response(cls, endpoint_func):
        @wraps(endpoint_func)
        def endpoint_wrapper_func(*args, **kwargs):
            if (response := endpoint_func(*args, **kwargs)) is not None:
                return response
            return cls.render_template()

        return endpoint_wrapper_func

    def _default_template_name(cls):
        template_folder, endpoint = request.endpoint.split(".")
        return f"{template_folder}/{endpoint}.{cls.template_file_ext}"

    def render_template(cls, template_name: Optional[str] = None, **context) -> str:
        ######### Set Globals #########
        g.template_name = template_name
        g.namespace = cls

        cls.template_name = template_name

        return render_template(
            template_name or cls._default_template_name(),
            **context,
        )

    def dependency_link(cls, file_extension):
        namespace_name, endpoint = request.endpoint.split(".")
        dependency_path = (
            f"/static/{file_extension}/{namespace_name}/{endpoint}.{file_extension}"
        )

        if file_extension == "css":
            return Markup(f'<link rel="stylesheet" href="{dependency_path}">')
        if file_extension == "js":
            return Markup(f'<script src="{dependency_path}"></script>')
        return dependency_path
