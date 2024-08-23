import inspect

from itsdangerous import URLSafeTimedSerializer

from .exceptions import OutsideScope
from .route import RouteNamespace


class Signer(URLSafeTimedSerializer):
    @classmethod
    def find_closest_route_namespace(cls):

        # Traverse the call stack and find BaseBlueprintNamespace
        for frame_info in inspect.stack():
            frame = frame_info.frame

            # Get the 'self' or 'cls' from the frame locals
            instance = frame.f_locals.get("self") or frame.f_locals.get("cls")

            if not (instance and isinstance(instance, RouteNamespace)):
                continue

            return instance

    @classmethod
    def get_scope(cls, scope: bool | type | str = True) -> str | None:
        if scope is False:
            return None

        if isinstance(scope, type):
            return scope.__name__

        if isinstance(scope, str):
            return scope

        if namespace_cls := cls.find_closest_route_namespace():
            return namespace_cls.__name__

        return None

    def dumps(
        self,
        obj,
        salt: str | bytes | None = None,
        scope: bool | type | str = True,
    ) -> str | bytes:

        # Wrap data in dictionary so configuration can be stored
        data = {"data": obj, "scope_str": self.get_scope(scope)}

        return super().dumps(data, salt)

    def loads(
        self,
        s: str | bytes,
        max_age: int | None = None,
        return_timestamp: bool = False,
        salt: str | bytes | None = None,
        scope: bool | type | str = True,
    ):
        parsed_data = super().loads(
            s,
            max_age=max_age,
            return_timestamp=return_timestamp,
            salt=salt,
        )

        if (
            previous_scope_str := parsed_data.get("scope_str")
        ) and previous_scope_str != (current_scope := self.get_scope(scope)):
            raise OutsideScope(
                f"Itsdangerous data attempted to be parsed outside of set scope_str. Previous scope_str: {previous_scope_str}, Current scope_str: {current_scope}"
            )

        return parsed_data.get("data") or parsed_data
