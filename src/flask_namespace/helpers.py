import re


def split_on_uppercase_char(string):
    return re.findall("[A-Z][^A-Z]*", str(string))


def cap_to_snake_case(string):
    return "_".join(split_on_uppercase_char(string)).lower()
