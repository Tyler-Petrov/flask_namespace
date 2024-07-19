from flask_namespace import helpers


def test_split_on_uppercase_char():
    string = "TestStr"
    lst = helpers.split_on_uppercase_char(string)
    assert lst == ["Test", "Str"], "The split wasn't on uppercase char"
