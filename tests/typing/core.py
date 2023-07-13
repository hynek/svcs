import contextlib
import sys

import svc_reg


reg = svc_reg.Registry()

reg.register_value(int, 1)
reg.register_value(int, 1, ping=lambda: None)
reg.register_value(int, 1, cleanup=lambda _: None)

reg.register_factory(str, str)
reg.register_value(str, str, ping=lambda: None)
reg.register_value(str, str, cleanup=lambda _: None)

con = svc_reg.Container(reg)

# The type checker believes whatever we tell it.
o1: object = con.get(object)
o2: int = con.get(object)

con.close()

with contextlib.closing(svc_reg.Container(reg)) as con:
    ...

if sys.version_info >= (3, 10):

    async def f() -> None:
        async with contextlib.aclosing(svc_reg.Container(reg)):
            ...
