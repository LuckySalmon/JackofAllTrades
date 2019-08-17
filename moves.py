import random, csv

# The class "Move" should be entirely self sufficient, and not require any numbers or variables outside of the class.

class Move:
    def __init__(self, attributes):
        self.name = attributes['Name'].title()
        self.dmg = (int(attributes['Lower Damage']), int(attributes['Upper Damage']))
        self.acc = int(attributes['Accuracy'])
        self.status = attributes['Status Effect']

    def getDamage(self):
        return random.randint(*self.dmg)     #what if we used triangular distribution (http://en.wikipedia.org/wiki/Triangular_distribution)? Perhaps even modify it based on accuracy?
    
    def getAccuracy(self):
        return self.acc
    
    def getStatus(self):
        return self.status
    
    def showStats(self):
        print(self.name)
        print('\tDamage:', self.dmg[0], '-', self.dmg[1])
        print('\tAccuracy:', str(self.acc) + '%')

moves = {}
with open('moves.csv', newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        moves[row['Name'].lower()] = Move(row)

defaultBasic = [moves['flick'], moves['punch'], moves['spit']]
boxerBasic = [moves['jab'], moves['cross'], moves['hook']]
psychoBasic =[moves['shank'], moves['stab'], moves['slice']]