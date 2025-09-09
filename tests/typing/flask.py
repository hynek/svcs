# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from collections.abc import Generator

import flask

import svcs


def factory_with_cleanup() -> Generator[int, None, None]:
    yield 1


reg = svcs.Registry()

app = flask.Flask("tests")
app = svcs.flask.init_app(app, registry=reg)
app = svcs.flask.init_app(app)

reg = svcs.flask.get_registry(app)

svcs.flask.register_value(app, int, 1)
svcs.flask.register_value(app, int, 1, ping=lambda: None)

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

con: svcs.Container = svcs.flask.svcs_from()
con = svcs.flask.svcs_from(flask.g)


class CustomApp(flask.Flask):
    pass


app = svcs.flask.init_app(CustomApp("tests"))
reg = svcs.flask.get_registry(CustomApp("tests"))

local_p: svcs.Container = svcs.flask.container
local_r: svcs.Registry = svcs.flask.registry
