import random
import json
from direct.showbase.MessengerGlobal import messenger


class Move:     # TODO: decide on whether these should be called moves or actions
    def __init__(self, name: str, damage: tuple[int, int], accuracy: int, effects):
        self.name = name
        self.damage = damage
        self.accuracy = accuracy
        self.effects = effects
        # TODO: effect system

    @classmethod
    def from_json(cls, file) -> 'Move':
        j = json.load(file)
        name = j.pop('name').title()
        return cls(name, **j)

    def apply(self, user, target):
        if self.accuracy > random.randint(0, 99):   # TODO: Should this be calculated based on more factors?
            damage = random.randint(*self.damage)   # TODO: Use a different distribution?
            if random.randint(1, 100) <= 2:
                damage *= 1.5
                msg = f"{user.Name}'s {self.name} hit for {damage} damage!\nCritical Hit!"
            else:
                msg = f"{user.Name}'s {self.name} hit for {damage} damage!"
        else:
            damage = 0
            msg = f"{user.Name}'s {self.name} missed!"

        messenger.send('output_info', [user.index, msg])
        target.apply_damage(damage)

    def info(self) -> str:
        """Return a string containing information about the move's damage and accuracy in a human-readable format."""
        return f'{self.name}\nDamage: {self.damage[0]} - {self.damage[1]}\nAccuracy: {self.accuracy}%'
