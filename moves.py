import random
import json
from typing import Any

from direct.showbase.MessengerGlobal import messenger


class Move:     # TODO: decide on whether these should be called moves or actions
    name: str
    damage: tuple[int, int]
    accuracy: int
    effects: Any
    target: str

    def __init__(self, name: str, damage: tuple[int, int], accuracy: int, effects, target: str = ''):
        self.name = name
        self.damage = damage
        self.accuracy = accuracy
        self.target = target
        self.effects = effects
        # TODO: effect system

    @classmethod
    def from_json(cls, file) -> 'Move':
        j = json.load(file)
        name = j.pop('name').title()
        return cls(name, **j)

    def apply(self, user, target, confirmed=False):
        if confirmed or self.accuracy > random.randint(0, 99):
            damage = random.randint(*self.damage)   # TODO: Use a different distribution?
            if random.randint(1, 100) <= 2:
                damage *= 1.5
                msg = f"{user.name}'s {self.name} hit for {damage} damage!\nCritical Hit!"
            else:
                msg = f"{user.name}'s {self.name} hit for {damage} damage!"
        else:
            damage = 0
            msg = f"{user.name}'s {self.name} missed!"

        messenger.send('output_info', [user.index, msg])
        target.apply_damage(damage)

    def info(self) -> str:
        """Return a string containing information about the move's damage and accuracy in a human-readable format."""
        return f'{self.name}\nDamage: {self.damage[0]} - {self.damage[1]}\nAccuracy: {self.accuracy}%'
