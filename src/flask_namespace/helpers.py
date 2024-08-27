import re

from flask import Flask


def split_on_uppercase_char(string):
    return re.findall("[A-Z][^A-Z]*", str(string))


def cap_to_snake_case(string):
    return "_".join(split_on_uppercase_char(string)).lower()


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


class classproperty(property):
    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)


class NamespaceBase:
    class_definition_suffix = "Namespace"

    @classproperty
    def url_prefix(cls):
        class_name_prefix = cls.__name__.replace(cls.class_definition_suffix, "")
        return f"/{class_name_prefix}"

    @classproperty
    def namespace_name(cls):
        return cap_to_snake_case(cls.url_prefix.replace("/", ""))
