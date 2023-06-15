from __future__ import annotations

import enum
import logging
from collections.abc import Container
from typing import TYPE_CHECKING, Any, Final
from typing_extensions import Self

import attrs

from .effects import Effect, EffectBundle, make_effect
from .skeletons import Side

if TYPE_CHECKING:
    from .characters import Fighter

_logger: Final = logging.getLogger(__name__)


class Target(enum.Enum):
    SELF = 'self'
    OTHER = 'opponent'


class MoveType(enum.Enum):
    MELEE = 'melee'
    RANGED = 'ranged'
    INSTANT = 'instant'
    REPOSITIONING = 'repositioning'


@attrs.define(kw_only=True)
class Move:  # TODO: decide on whether these should be called moves or actions
    name: str
    type: MoveType
    accuracy: int = 100
    effect: Effect | None = None
    side: Side | None = None
    valid_targets: Container[Target] = frozenset()
    target_part: str = 'torso'

    def __str__(self) -> str:
        return f'{type(self).__name__} {self.name!r}'

    @classmethod
    def from_json(cls, j: dict[str, Any]) -> Self:
        name = j.pop('name').title()
        target = j.pop('target').lower()
        valid_targets = set[Target]()
        if target in ('self', 'any'):
            valid_targets.add(Target.SELF)
        if target in ('other', 'any'):
            valid_targets.add(Target.OTHER)
        effect_params = j.pop('effects', None)
        if effect_params is None:
            effect = None
        else:
            effect = EffectBundle([make_effect(**params) for params in effect_params])
        move_type = MoveType[j.pop('type').upper()]
        side_string = j.pop('side', None)
        side = None if side_string is None else Side[side_string.upper()]
        return cls(
            name=name,
            type=move_type,
            side=side,
            **j,
            valid_targets=valid_targets,
            effect=effect,
        )

    def apply(self, user: Fighter, target: Fighter) -> None:
        _logger.debug(f'{user} hit {target} with {self}')
        if self.effect is not None:
            self.effect.apply(target)
