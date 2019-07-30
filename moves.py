import random

# The class "Move" should be entirely self sufficient, and not require any numbers or variables outside of the class.

class Move:
    def __init__(self, name, dmg, acc, status=''):
        self.name = name.title()
        self.dmg = dmg
        self.acc = acc
        self.status = status

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

flick = Move('flick', (0, 1), 100)
punch = Move('punch', (5, 15), 90)
spit = Move('spit', (0, 0), 55, 'gross')
defaultBasic = [flick, punch, spit]

jab = Move('jab', (5, 10), 95)
cross = Move('cross', (8, 20), 85)
hook = Move('hook', (12, 15), 85)
boxerBasic = [jab, cross, hook]

shank = Move('shank', (20, 25), 75)
stab = Move('stab', (23, 30), 65)
slice = Move('slice', (15, 20), 85)
psychoBasic =[shank, stab, slice]