import csv
import random
import os
import json


# The class "Move" should be entirely self sufficient, and not require any numbers or variables outside of the class.

class Move:
    def __init__(self, attributes):
        self.name = attributes['name'].title()
        self.dmg = attributes['damage']
        self.acc = int(attributes['accuracy'])
        self.status = attributes['effects']

    def get_damage(self):
        """Return a value within the damage bounds."""
        return random.randint(*self.dmg)
        # TODO:
        #  what if we used triangular distribution (http://en.wikipedia.org/wiki/Triangular_distribution)?
        #  Perhaps even modify it based on accuracy?

    def get_accuracy(self):
        """Return the accuracy of the move."""
        return self.acc

    def get_status(self):
        """Return the status effects of the move."""
        return self.status

    def show_stats(self):
        """Return a string containing information about the move's damage and accuracy in a human-readable format."""
        return '{0}\nDamage: {1} - {2}\nAccuracy: {3}%'.format(self.name, self.dmg[0], self.dmg[1], str(self.acc))


moves = {}
for file in os.scandir('data\\moves'):
    with open(file) as f:
        j = json.load(f)
        moves[j['name']] = Move(j)

sets = {}
for file in os.scandir('data\\sets'):
    with open(file) as f:
        j = json.load(f)
        sets[j['name']] = j['moves']

defaultBasic = [moves['flick'], moves['punch'], moves['spit']]
