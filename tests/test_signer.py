# When running file without pytest export PYTHONPATH="${PYTHONPATH}:./src"


import pytest
from itsdangerous import URLSafeTimedSerializer

from flask_namespace.exceptions import OutsideScope
from flask_namespace.route import RouteNamespace
from flask_namespace.signer import Signer

secret_key = "Super Secret Key"


def test_loads_dumps():
    signer = Signer(secret_key)

    start_unsigned_val = {"key": "value"}
    signed_val = signer.dumps(start_unsigned_val)
    end_unsigned_val = signer.loads(signed_val)

    assert (
        start_unsigned_val == end_unsigned_val
    ), "Signer returned a different value then was expected"


def test_scope():
    signer = Signer(secret_key)

    start_unsigned_val = {"key": "value"}

    class Scope1:
        pass

    class Scope2:
        pass

    def run_scope_test(first_scope, second_scope):
        signed_val = signer.dumps(start_unsigned_val, scope=first_scope)
        signer.loads(signed_val, scope=second_scope)

    # ####### Check inside scope_str #######
    run_scope_test("Scope1", "Scope1")
    run_scope_test(Scope1, Scope1)

    ####### Check outside scope_str #######
    with pytest.raises(OutsideScope):
        run_scope_test("Scope1", "Scope2")
        run_scope_test(Scope1, Scope2)

    ####### Check inside Namespace classes #######
    class SignerNamespace(RouteNamespace):
        def load_data(cls, signed_data):
            return signer.loads(signed_data)

        def check_scope(cls, signed_data):
            # Create serializer that will show the scope_str in the json data
            serializer = URLSafeTimedSerializer(secret_key)

            # Parse the signed data with serializer
            json_data = serializer.loads(signed_data)

            # Get the scope_str of the signed data
            scope_str = json_data["scope_str"]

            # Check that scope_str is the same as when it was signed
            if scope_str != cls.__name__:
                raise OutsideScope(
                    f"scope_str={scope_str} cls_name={cls.__name__} "
                    "The scope_str of the signed data isn't derived from the closest RouteNamespace class"
                )

    class Namespace1(SignerNamespace):
        @classmethod
        def dump_data(cls):
            dumped_data = {
                "key": "value",
                "class": "Namespace1",
            }
            return signer.dumps(dumped_data)

    class Namespace2(SignerNamespace):
        @classmethod
        def dump_data(cls):
            dumped_data = {
                "key": "value",
                "class": "Namespace2",
            }
            return signer.dumps(dumped_data)

    Namespace1.check_scope(signed_data=Namespace1.dump_data())
    Namespace2.check_scope(signed_data=Namespace2.dump_data())

    with pytest.raises(OutsideScope):
        Namespace1.check_scope(signed_data=Namespace2.dump_data())
        Namespace2.check_scope(signed_data=Namespace1.dump_data())


test_scope()
