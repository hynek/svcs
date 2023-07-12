from flask import Flask

import svc_reg
import svc_reg.flask as f


reg = svc_reg.Registry()

app = Flask("tests")
app = f.init_app(app, reg)
app = f.init_app(app)

f.register_value(int, 1)
f.register_value(int, 1, ping=lambda: None)
f.register_value(int, 1, cleanup=lambda _: None)

f.register_factory(str, str)
f.register_value(str, str, ping=lambda: None)
f.register_value(str, str, cleanup=lambda _: None)

# The type checker believes whatever we tell it.
o1: object = f.get(object)
o2: int = f.get(object)
