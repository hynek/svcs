# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT


from typing import Annotated  # noqa: F401


def nop(*_, **__):
    pass


class CloseMe:
    is_aclosed = is_closed = False

    def close(self):
        self.is_closed = True

    async def aclose(self):
        self.is_aclosed = True
