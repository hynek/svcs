# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

import sys


if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    from typing_extensions import Annotated  # noqa: F401


def nop(*_, **__):
    pass


class CloseMe:
    is_aclosed = is_closed = False

    def close(self):
        self.is_closed = True

    async def aclose(self):
        self.is_aclosed = True
