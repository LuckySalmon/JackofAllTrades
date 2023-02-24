from __future__ import annotations

import enum
import json
import logging
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Final, TypeAlias

from direct.showbase.MessengerGlobal import messenger

if TYPE_CHECKING:
    from _typeshed import SupportsRead

    from .characters import Fighter

_logger: Final = logging.getLogger(__name__)

# These should ideally return `None`, but using a function
# with a return value won't have any ill effects.
EffectProcedure: TypeAlias = 'Callable[[Fighter], object]'


def noop(*_: object) -> None:
    """Accept arbitrary positional arguments and do nothing."""
    pass


class Target(enum.Enum):
    SELF = enum.auto()
    OTHER = enum.auto()


@dataclass
class InstantEffect:
    name: str
    apply: EffectProcedure

    def __str__(self) -> str:
        return f'{type(self).__name__} {self.name!r}'

    @classmethod
    def from_preset(cls, name: str, *args: Any, **kwargs: Any) -> InstantEffect:
        constructor = INSTANT_EFFECT_CONSTRUCTORS.get(name)
        if constructor is None:
            raise ValueError(f'Could not find a constructor for effect {name!r}')
        return constructor(*args, **kwargs)


@dataclass(kw_only=True)
class StatusEffect:
    name: str = field(kw_only=False)
    duration: int = field(kw_only=False)
    on_application: EffectProcedure = field(default=noop, repr=False)
    on_turn: EffectProcedure = field(default=noop, repr=False)
    on_removal: EffectProcedure = field(default=noop, repr=False)

    def __str__(self) -> str:
        return f'{type(self).__name__} {self.name!r}'

    @classmethod
    def from_preset(cls, name: str, strength: int, duration: int) -> StatusEffect:
        constructor = STATUS_EFFECT_CONSTRUCTORS.get(name)
        if constructor is not None:
            return constructor(strength, duration)
        else:
            return cls(name, duration)

    def is_active(self) -> bool:
        return self.duration > 0


@dataclass(kw_only=True)
class Move:  # TODO: decide on whether these should be called moves or actions
    name: str = field(kw_only=False)
    accuracy: int
    instant_effects: list[InstantEffect] = field(default_factory=list)
    status_effects: list[StatusEffect] = field(default_factory=list)
    using: str = ''
    target: str = ''
    target_part: str = 'torso'
    is_projectile: bool = False
    # TODO: effect system

    def __str__(self) -> str:
        return f'{type(self).__name__} {self.name!r}'

    @classmethod
    def from_json(cls, file: SupportsRead[str | bytes]) -> Move:
        j = json.load(file)
        name = j.pop('name').title()
        instant_effects = [
            InstantEffect.from_preset(**params)
            for params in j.pop('instant_effects', [])
        ]
        status_effects = [
            StatusEffect.from_preset(**params)
            for params in j.pop('status_effects', [])  # fmt: off
        ]
        return cls(
            name,
            **j,
            instant_effects=instant_effects,
            status_effects=status_effects,
        )

    def apply(self, user: Fighter, target: Fighter, confirmed: bool = False) -> None:
        if confirmed or self.accuracy > random.randint(0, 99):
            _logger.debug(f'{user} hit {target} with {self}')
            for instant_effect in self.instant_effects:
                _logger.debug(f'Applying {instant_effect} to {target}')
                instant_effect.apply(target)
            target.copy_effects(self.status_effects)
        else:
            _logger.debug(f'{user} missed {target} with {self}')
            messenger.send('output_info', [f"{user.name}'s {self.name} missed!"])


def make_damage_effect(lower_bound: int, upper_bound: int) -> InstantEffect:
    def apply_damage(target: Fighter) -> None:
        # TODO: Use a different distribution?
        damage = random.randint(lower_bound, upper_bound)
        if random.randint(1, 100) <= 2:
            damage = 3 * damage // 2
        target.apply_damage(damage)

    return InstantEffect("damage", apply_damage)


def make_cleanse_effect() -> InstantEffect:
    def cleanse(target: Fighter) -> None:
        for effect in target.status_effects:
            effect.on_removal(target)
        target.status_effects.clear()

    return InstantEffect('cleanse', cleanse)


INSTANT_EFFECT_CONSTRUCTORS: dict[str, Callable[..., InstantEffect]] = {
    'damage': make_damage_effect,
    'cleanse': make_cleanse_effect,
}


def make_poison_effect(strength: int, duration: int) -> StatusEffect:
    def poison(target: Fighter) -> None:
        target.apply_damage(strength)

    return StatusEffect('poison', duration, on_turn=poison)


def make_invisibility_effect(strength: int, duration: int) -> StatusEffect:
    old_debug_values: dict[str, bool] = {}

    def apply_invisibility(target: Fighter) -> None:
        for name, part in target.skeleton.parts.items():
            old_debug_values[name] = part.node().debug_enabled
            part.node().debug_enabled = False

    def remove_invisibility(target: Fighter) -> None:
        for name, part in target.skeleton.parts.items():
            part.node().debug_enabled = old_debug_values[name]

    return StatusEffect(
        'invisibility',
        duration,
        on_application=apply_invisibility,
        on_removal=remove_invisibility,
    )


STATUS_EFFECT_CONSTRUCTORS: dict[str, Callable[[int, int], StatusEffect]] = {
    'poison': make_poison_effect,
    'invisibility': make_invisibility_effect,
}
