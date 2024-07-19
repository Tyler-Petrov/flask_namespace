# When running file without pytest export PYTHONPATH="${PYTHONPATH}:./src"


import pytest
from itsdangerous import URLSafeTimedSerializer

from flask_namespace import Namespace, Signer
from flask_namespace.exceptions import OutsideLocality

secret_key = "Super Secret Key"


def test_loads_dumps():
    signer = Signer(secret_key)

    start_unsigned_val = {"key": "value"}
    signed_val = signer.dumps(start_unsigned_val)
    end_unsigned_val = signer.loads(signed_val)

    assert (
        start_unsigned_val == end_unsigned_val
    ), "Signer returned a different value then was expected"


def test_locality():
    signer = Signer(secret_key)

    start_unsigned_val = {"key": "value"}

    class Locality1:
        pass

    class Locality2:
        pass

    def run_locality_test(first_locality, second_locality):
        signed_val = signer.dumps(start_unsigned_val, local=first_locality)
        signer.loads(signed_val, local=second_locality)

    # ####### Check inside locality #######
    run_locality_test("Locality1", "Locality1")
    run_locality_test(Locality1, Locality1)

    ####### Check outside locality #######
    with pytest.raises(OutsideLocality):
        run_locality_test("Locality1", "Locality2")
        run_locality_test(Locality1, Locality2)

    ####### Check inside Namespace classes #######
    class SignerNamespace(Namespace):
        def load_data(cls, signed_data):
            return signer.loads(signed_data)

        def check_locality(cls, signed_data):
            # Create serializer that will show the locality in the json data
            serializer = URLSafeTimedSerializer(secret_key)

            # Parse the signed data with serializer
            json_data = serializer.loads(signed_data)

            # Get the locality of the signed data
            locality = json_data["locality"]

            # Check that locality is the same as when it was signed
            if locality != cls.__name__:
                raise OutsideLocality(
                    f"locality={locality} cls_name={cls.__name__} The locality of the signed data isn't derived from the closest Namespace class"
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

    Namespace1.check_locality(signed_data=Namespace1.dump_data())
    Namespace2.check_locality(signed_data=Namespace2.dump_data())

    with pytest.raises(OutsideLocality):
        Namespace1.check_locality(signed_data=Namespace2.dump_data())
        Namespace2.check_locality(signed_data=Namespace1.dump_data())


test_locality()
