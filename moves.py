import csv
import random


# The class "Move" should be entirely self sufficient, and not require any numbers or variables outside of the class.

class Move:
    def __init__(self, attributes):
        self.name = attributes['name'].title()
        self.dmg = (int(attributes['lower damage']), int(attributes['upper damage']))
        self.acc = int(attributes['accuracy'])
        self.status = attributes['status effect']

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
with open('moves.csv', newline='') as file:
    reader = csv.DictReader(file)
    for row in reader:
        moves[row['name']] = Move(row)

sets = {}
with open('sets.csv', newline='') as file:
    for row in (reader := csv.reader(file)):
        moveList = []
        for move in row[1:]:
            moveList.append(moves[move])
        sets[row[0]] = moveList

defaultBasic = [moves['flick'], moves['punch'], moves['spit']]
