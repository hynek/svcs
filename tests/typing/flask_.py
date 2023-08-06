# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from typing import Generator

from flask import Flask

import svcs


def factory_with_cleanup() -> Generator[int, None, None]:
    yield 1


reg = svcs.Registry()

app = Flask("tests")
app = svcs.flask.init_app(app, reg)
app = svcs.flask.init_app(app)

svcs.flask.replace_value(int, 1)
svcs.flask.replace_value(int, 1, ping=lambda: None)

svcs.flask.register_value(app, int, 1)
svcs.flask.register_value(app, int, 1, ping=lambda: None)

svcs.flask.replace_factory(str, str)
svcs.flask.replace_value(str, str, ping=lambda: None)

svcs.flask.register_factory(app, str, str)
svcs.flask.register_factory(app, int, factory_with_cleanup)
svcs.flask.register_value(app, str, str, ping=lambda: None)

o1: object = svcs.flask.get(object)

a: int
b: str
c: bool
d: tuple
e: object
f: float
g: list
h: dict
i: set
j: bytes
a, b, c, d, e, f, g, h, i, j = svcs.flask.get(
    int, str, bool, tuple, object, float, list, dict, set, bytes
)


svcs.flask.close_registry(app)


class CustomApp(Flask):
    pass


app = svcs.flask.init_app(CustomApp("tests"))
