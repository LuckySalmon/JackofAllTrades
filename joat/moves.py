from __future__ import annotations

import enum
import logging
import random
from collections.abc import Container
from typing import TYPE_CHECKING, Any, Final
from typing_extensions import Self

import attrs
from direct.showbase.MessengerGlobal import messenger

from .effects import Effect, EffectBundle, make_effect

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
    accuracy: int
    effect: Effect | None = None
    using: str = ''
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
        return cls(
            name=name,
            type=move_type,
            **j,
            valid_targets=valid_targets,
            effect=effect,
        )

    def apply(self, user: Fighter, target: Fighter, confirmed: bool = False) -> None:
        if confirmed or self.accuracy > random.randint(0, 99):
            _logger.debug(f'{user} hit {target} with {self}')
            if self.effect is not None:
                self.effect.apply(target)
        else:
            _logger.debug(f'{user} missed {target} with {self}')
            messenger.send('output_info', [f"{user.name}'s {self.name} missed!"])
