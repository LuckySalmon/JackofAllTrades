import random, csv

# The class "Move" should be entirely self sufficient, and not require any numbers or variables outside of the class.

class Move:
    def __init__(self, attributes):
        self.name = attributes['name'].title()
        self.dmg = (int(attributes['lower damage']), int(attributes['upper damage']))
        self.acc = int(attributes['accuracy'])
        self.status = attributes['status effect']

    def getDamage(self):
        return random.randint(*self.dmg)   #what if we used triangular distribution (http://en.wikipedia.org/wiki/Triangular_distribution)? Perhaps even modify it based on accuracy?
    
    def getAccuracy(self):
        return self.acc
    
    def getStatus(self):
        return self.status
    
    def showStats(self):
        return '{0}\nDamage: {1} - {2}\nAccuracy: {3}%'.format(self.name, self.dmg[0], self.dmg[1], str(self.acc))

moves = {}
with open('moves.csv', newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        moves[row['name']] = Move(row)
sets = {}
with open('sets.csv', newline='') as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
        moveList = []
        for move in row[1:]:
            moveList.append(moves[move])
        sets[row[0]] = moveList

defaultBasic = [moves['flick'], moves['punch'], moves['spit']]
