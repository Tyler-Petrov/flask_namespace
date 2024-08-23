from flask import Blueprint, Flask

from flask_namespace.route import RouteNamespace


def get_blueprint_endpoints(app: Flask, blueprint: Blueprint):
    return [
        (rule.rule, rule.endpoint)
        for rule in app.url_map.iter_rules()
        if rule.endpoint.startswith(blueprint.name + ".")
    ]


def test_route():
    app = Flask(__name__)

    class TestRoutes(RouteNamespace):
        def get_get(cls):
            return cls.render_template("test.jinja")

        def post_post(cls):
            return cls.render_template("test.jinja")

    TestRoutes.register_namespace(app)

    for bp_name, bp in app.blueprints.items():
        assert bp_name == "test", "Blueprint Name isn't correct"

        endpoints = get_blueprint_endpoints(app, bp)

        get_rule, get_endpoint = endpoints[0]
        assert get_rule == "/Test/get", "Endpoint rule not set correctly"
        assert get_endpoint == "test.get", "Endpoint name not set correctly"

        post_rule, post_endpoint = endpoints[1]
        assert post_rule == "/Test/post", "Endpoint rule not set correctly"
        assert post_endpoint == "test.post", "Endpoint name not set correctly"
