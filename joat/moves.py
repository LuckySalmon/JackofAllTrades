import json
import random
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, TypeAlias

from direct.showbase.MessengerGlobal import messenger

if TYPE_CHECKING:
    from _typeshed import SupportsRead

    from .characters import Fighter


# These should ideally return `None`, but using a function
# with a return value won't have any ill effects.
EffectProcedure: TypeAlias = 'Callable[[Fighter], object]'


def noop(*_: object) -> None:
    """Accept arbitrary positional arguments and do nothing."""
    pass


@dataclass
class StatusEffect:
    name: str
    duration: int
    #  The following are assigned to fields because assigning
    #  them to a function directly confuses the IDE.
    on_application: EffectProcedure = field(default=noop)
    on_turn: EffectProcedure = field(default=noop)
    on_removal: EffectProcedure = field(default=noop)

    @classmethod
    def from_preset(cls, name: str, strength: int, duration: int) -> 'StatusEffect':
        constructor = EFFECT_CONSTRUCTORS.get(name)
        if constructor is not None:
            return constructor(strength, duration)
        else:
            return cls(name, duration)

    def is_active(self) -> bool:
        return self.duration > 0


@dataclass
class Move:  # TODO: decide on whether these should be called moves or actions
    name: str
    damage: tuple[int, int]
    accuracy: int
    effects: list[StatusEffect]
    target: str = ''
    target_part: str = ''
    # TODO: effect system

    @classmethod
    def from_json(cls, file: 'SupportsRead[str | bytes]') -> 'Move':
        j = json.load(file)
        name = j.pop('name').title()
        effect_params = j.pop('effects')
        effects = [StatusEffect.from_preset(**params) for params in effect_params]
        return cls(name, **j, effects=effects)

    def apply(self, user: 'Fighter', target: 'Fighter',
              confirmed: bool = False) -> None:
        if confirmed or self.accuracy > random.randint(0, 99):
            damage = random.randint(*self.damage)  # TODO: Use a different distribution?
            template = "{}'s {} hit for {} damage!"
            if random.randint(1, 100) <= 2:
                damage = 3 * damage // 2
                template += '\nCritical Hit!'
            for effect in self.effects:
                target.add_effect(replace(effect))
        else:
            damage = 0
            template = "{}'s {} missed!"
        messenger.send(
            'output_info',
            [user.index, template.format(user.name, self.name, damage)]
        )
        target.apply_damage(damage)

    def info(self) -> str:
        """Return a string containing information about the move's
        damage and accuracy in a human-readable format.
        """
        return '\n'.join((
            self.name,
            f'{self.damage[0]} - {self.damage[1]}',
            f'{self.accuracy}%',
        ))


def make_poison_effect(strength: int, duration: int) -> 'StatusEffect':
    def poison(target: 'Fighter') -> None:
        target.apply_damage(strength)
    return StatusEffect('poison', duration, on_turn=poison)


EFFECT_CONSTRUCTORS: 'dict[str, Callable[[int, int], StatusEffect]]' = {
    'poison': make_poison_effect,
}
