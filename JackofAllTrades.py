import random

# The class "Moves" should be entirely self sufficient and not require any numbers or
#variables outside of the class.


class Moves:
    def __init__(self, name, dmg, acc, status):
        self.dmg = dmg
        self.acc = acc
        self.status = status

    def getDamage(self):
        return random.randint(*self.dmg)
    
    def getAccuracy(self):
        return random.randint(*self.acc)
    
    def getStatus(self):
        return status

    
class Character:
    
    def __init__(self, Name, StartingHP, HP, Speed, Defence, XP):
        self.StartingHP = StartingHP
        self.CurrentHP = HP
        self.Speed = Speed
        self.Defence = Defence
        self.XP = XP
        self.Name = Name
        self.moveList = []
        self.Level = 1
        
    def moveList(self):
        #check what moves this character has and return a list of availible moves
        print(self.moveList)

    def addMove(self,name):
        #check that only the correct number of moves is added to the list and give options to replace a move
        if self.moveList.len() <= int(0.41 * self.Level +4):
            self.moveList.append(name)
        else:
            print("You have too many moves. Would you like to replace one?")
            
    
    def getLevel(self):
        T = self.level * 1000
        if self.XP >= T:
            self.Level +=1
            self.XP = 0
        return self.Level
    
    def displayHP(self):
        print (self.CurrentHP)

