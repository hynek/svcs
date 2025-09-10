# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from typing import NewType

import svcs


reg = svcs.Registry()
con = svcs.Container(reg)

S1 = NewType("S1", str)
S2 = NewType("S2", str)

reg.register_value(S1, "foo")
reg.register_value(S2, "bar")

s1: str = con.get(S1)
s2: str = con.get(S2)
