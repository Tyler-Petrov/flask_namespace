import inspect
from typing import Callable, Optional

from flask import Blueprint, Flask, g, render_template, request

from flask_namespace.helpers import ClassMethodsMeta, NamespaceBase, set_jinja_global

app_context: Flask | None = None


class RouteNamespace(NamespaceBase, metaclass=ClassMethodsMeta):
    class_definition_suffix = "Routes"
    template_file_ext = "jinja"

    @staticmethod
    def route_prefix_to_http_method(route_method_name):
        split_name = route_method_name.split("_")
        route_prefix, route_endpoint = split_name[0], "_".join(split_name[1:])
        conversion_key = {"get": ["GET"], "post": ["POST"], "form": ["GET", "POST"]}

        return route_prefix, route_endpoint, conversion_key.get(route_prefix)

    def prepare_endpoint(cls, endpoint_func: Callable):
        return endpoint_func

    def format_endpoint_name(cls, endpoint_name: str) -> str:
        return endpoint_name

    def compute_url(cls, route_method: Callable):
        # Parse the route_method name
        _, route_endpoint, _ = cls.route_prefix_to_http_method(route_method.__name__)

        # Get the non cls parameters from the route's method in list<str> format
        url_params = [
            str(param) for param in inspect.signature(route_method).parameters.values()
        ]

        # Join the remaining method params with a trailing /
        url_param_str = "".join([f"/<{param}>" for param in url_params])

        # Replace the underscores with dashes for the url
        route_url_suffix = route_endpoint.replace("_", "-")

        return f"{url_param_str}/{route_url_suffix}"

    def register_namespace(cls, app: Flask):
        app_context = app

        cls.blueprint = Blueprint(
            cls.namespace_name, __name__, url_prefix=cls.url_prefix
        )

        for attr_name in dir(cls):
            # Get the prefix, and the corresponding http methods
            _, route_endpoint, http_methods = cls.route_prefix_to_http_method(attr_name)

            # If the attribute name isn't matched as a route
            if not http_methods:
                continue

            # Get the method from the class by the attribute name
            route_method = getattr(cls, attr_name)

            # Call modifier class methods
            prepared_endpoint = cls.prepare_endpoint(route_method)
            endpoint_name = cls.format_endpoint_name(route_endpoint)
            endpoint_url = cls.compute_url(route_method)

            # Save the route to the blueprint
            cls.blueprint.route(
                endpoint_url,
                methods=http_methods,
                endpoint=endpoint_name,
            )(prepared_endpoint)

        # Register the blueprint to the flask app
        app_context.register_blueprint(cls.blueprint)

    def _default_template_name(cls):
        template_folder, endpoint = request.endpoint.split(".")
        return f"{template_folder}/{endpoint}.{cls.template_file_ext}"

    def render_template(cls, template_name: Optional[str] = None, **context) -> str:
        ######### Set Globals #########
        g.template_name = template_name
        g.namespace = cls

        set_jinja_global(app_context, "nsp", cls)
        cls.template_name = template_name

        return render_template(
            template_name or cls._default_template_name(),
            **context,
        )
