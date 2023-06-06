from __future__ import annotations

import logging
import random
from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Final, Protocol

import attrs

if TYPE_CHECKING:
    from .characters import Fighter

_logger: Final = logging.getLogger(__name__)


class Effect(Protocol):
    def apply(self, fighter: Fighter) -> None:
        pass


class StatusEffect(Protocol):
    duration: int

    def apply(self, fighter: Fighter) -> None:
        fighter.add_effect(attrs.evolve(self))

    def on_application(self, fighter: Fighter) -> None:
        pass

    def on_turn(self, fighter: Fighter) -> None:
        pass

    def on_removal(self, fighter: Fighter) -> None:
        pass

    def is_active(self) -> bool:
        return self.duration > 0


@attrs.define
class EffectBundle:
    effects: Iterable[Effect] = ()

    def apply(self, fighter: Fighter) -> None:
        for effect in self.effects:
            _logger.debug(f'Applying {effect} to {fighter}')
            effect.apply(fighter)


@attrs.define
class DamageEffect:
    lower_bound: int
    upper_bound: int

    def apply(self, fighter: Fighter) -> None:
        damage = random.randint(self.lower_bound, self.upper_bound)
        if random.randint(1, 100) <= 2:
            damage = 3 * damage // 2
        fighter.apply_damage(damage)


@attrs.define
class CleanseEffect:
    def apply(self, fighter: Fighter) -> None:
        for effect in fighter.status_effects:
            effect.on_removal(fighter)
        fighter.status_effects.clear()


@attrs.define
class PoisonEffect(StatusEffect):
    strength: int
    duration: int

    def on_turn(self, fighter: Fighter) -> None:
        fighter.apply_damage(self.strength)


@attrs.define
class InvisibilityEffect(StatusEffect):
    duration: int
    _old_debug_values: dict[str, bool] = attrs.field(factory=dict, init=False)

    def on_application(self, fighter: Fighter) -> object:
        for name, part in fighter.skeleton.parts.items():
            self._old_debug_values[name] = part.node().debug_enabled
            part.node().debug_enabled = False

    def on_removal(self, fighter: Fighter) -> object:
        for name, part in fighter.skeleton.parts.items():
            part.node().debug_enabled = self._old_debug_values[name]


EFFECT_CONSTRUCTORS: dict[str, Callable[..., Effect]] = {
    'damage': DamageEffect,
    'cleanse': CleanseEffect,
    'poison': PoisonEffect,
    'invisibility': InvisibilityEffect,
}


def make_effect(name: str, *args, **kwargs) -> Effect:
    constructor = EFFECT_CONSTRUCTORS.get(name)
    if constructor is None:
        raise ValueError(f'Could not find a constructor for effect {name!r}')
    return constructor(*args, **kwargs)
