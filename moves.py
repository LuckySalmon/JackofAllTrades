import random
import json
from direct.showbase.MessengerGlobal import messenger


# The class "Move" should be entirely self sufficient, and not require any numbers or variables outside of the class.

class Move:
    def __init__(self, name: str, damage: tuple[int, int], accuracy: int, effects):
        self.name = name
        self.dmg = damage
        self.acc = accuracy
        self.status = effects

    @classmethod
    def from_json(cls, file) -> 'Move':
        j = json.load(file)
        name = j.pop('name').title()
        return cls(name, **j)

    def apply(self, user, target):
        if self.acc > random.randint(0, 99):    # TODO: Should this be calculated based on more factors?
            damage = random.randint(*self.dmg)  # TODO: Use a different distribution?
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

    def get_accuracy(self) -> float:
        """Return the accuracy of the move."""
        return self.acc

    def get_status(self):
        """Return the status effects of the move."""
        return self.status

    def show_stats(self) -> str:
        """Return a string containing information about the move's damage and accuracy in a human-readable format."""
        return '{0}\nDamage: {1} - {2}\nAccuracy: {3}%'.format(self.name, self.dmg[0], self.dmg[1], str(self.acc))
