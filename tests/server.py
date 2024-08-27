from flask import Flask, g, render_template_string

from flask_namespace import Namespace, nsp
from flask_namespace.route import RouteNamespace

app = Flask(__name__)
namespace = Namespace(app)


class TestRoutes(RouteNamespace):
    def test(cls):
        return nsp

    def get_index(cls):
        print(nsp)
        return render_template_string(
            """\
{{ nsp.test() }}\
"""
        )


namespace.register_namespace(TestRoutes)


class NewRoutes(RouteNamespace):
    def test(cls):
        return nsp

    def get_index(cls):
        print(nsp)
        return render_template_string(
            """\
{{ nsp.test() }}\
"""
        )


namespace.register_namespace(NewRoutes)


@app.get("/")
def index():
    return render_template_string(
        """\
{{ nsp }}\
"""
    )


if __name__ == "__main__":
    app.run(debug=True)
