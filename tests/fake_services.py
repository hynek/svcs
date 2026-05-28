# SPDX-FileCopyrightText: 2023 Hynek Schlawack <hs@ox.cx>
#
# SPDX-License-Identifier: MIT

from dataclasses import InitVar, dataclass

from tests.ifaces import (
    AnotherService,
    Service,
    UnregisteredService,
    YetAnotherService,
)


@dataclass
class SingleService:
    svc: Service


@dataclass
class MultipleServices:
    svc: Service
    another: AnotherService


@dataclass
class KeywordArgWithDefault:
    svc: Service
    optional: UnregisteredService | None = None


@dataclass(init=False)
class PositionalOnlyArgWithDefault:
    svc: Service
    optional: UnregisteredService | None

    def __init__(
        self,
        svc: Service,
        optional: UnregisteredService | None = None,
        /,
    ) -> None:
        self.svc = svc
        self.optional = optional


@dataclass(init=False)
class KeywordOnlyServices:
    svc: Service
    another: AnotherService

    def __init__(self, *, svc: Service, another: AnotherService) -> None:
        self.svc = svc
        self.another = another


@dataclass(init=False)
class PositionalOnlyServices:
    svc: Service
    another: AnotherService
    yet_another: YetAnotherService

    def __init__(
        self,
        svc: Service,
        another: AnotherService,
        /,
        yet_another: YetAnotherService,
    ) -> None:
        self.svc = svc
        self.another = another
        self.yet_another = yet_another


@dataclass(init=False)
class VariadicArgs:
    svc: Service
    args: tuple[str, ...]
    kwargs: dict[str, int]

    def __init__(self, svc: Service, *args: str, **kwargs: int) -> None:
        self.svc = svc
        self.args = args
        self.kwargs = kwargs


@dataclass(eq=False)
class InitVarService:  # noqa: PLW1641
    service: Service
    another: InitVar[AnotherService]

    def __post_init__(self, another: InitVar[AnotherService]) -> None:
        self.another = another

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, InitVarService):
            return NotImplemented

        return self.service == other.service and self.another == other.another
