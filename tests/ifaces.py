# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

"""
Interfaces used throughout the tests. They're dataclasses so they have a
predicatable repr.
"""

import dataclasses


@dataclasses.dataclass
class Service:
    pass


@dataclasses.dataclass
class AnotherService:
    pass


@dataclasses.dataclass
class YetAnotherService:
    pass
