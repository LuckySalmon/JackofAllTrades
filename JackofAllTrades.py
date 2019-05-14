import random

# The class "Moves" should be entirely self sufficient, and not require any numbers or
#variables outside of the class.


class Moves:
    def __init__(self, Dmg, Acc, Status):
        self.Dmg = Dmg
        self.Acc = Acc
        self.Status = Status

    def getDamage(self):
        return random.randint(self.dmg[0],self.dmg[1])
    def getAccuracy(self):
        return random.randint(self.Acc[0],self.Acc[1])
    def getStatus(self):
        return Status

    
class Character:
    def __init__(self, Name, StartingHP, HP, Speed, Defence, XP):
        self.StartingHP = StartingHP
        self.CurrentHP = HP
        self.Speed = Speed
        self.Defence = Defence
        self.XP = XP
        self.Name = Name

    def moveList(self):
        #check what moves this person has and return a list of availible moves
        pass
    def getLevel(XP):
        pass
    def displayHP(self):
        print (self.CurrentHP)

