import random, winsound

# The class "Moves" should be entirely self sufficient, and not require any numbers or variables outside of the class.


class Moves:
    def __init__(self, name, dmg, acc, status):
        self.dmg = dmg
        self.acc = acc
        self.status = status

    def getDamage(self):
        winsound.Beep(2000, 250)
        return random.randint(self.dmg[0],self.dmg[1])
    
    def getAccuracy(self):
        winsound.Beep(2000, 250)
        return random.randint(self.acc[0],self.acc[1])
    
    def getStatus(self):
        winsound.Beep(2000, 250)
        return status

    
class Character:
    
    def __init__(self, Name, StartingHP, HP, Speed, Defence, XP):
        self.StartingHP = StartingHP
        self.CurrentHP = HP
        self.Speed = Speed
        self.Defence = Defence
        self.XP = XP
        self.Name = Name
        self.moveList =  []
        self.Level = 1
        
    def moveList(self):
        #check what moves this person has and return a list of availible moves
        print(self.moveList)
        winsound.Beep(2000, 250)

    def addMove(self,name):
        #check that the only the correct number of moves is added to the list and give options to replace a move
        if self.moveList.len() <= int(0.41 * self.Level +4):
            self.moveList.append(name)
            winsound.Beep(2000, 250)    # This makes a friendly little chirp whenever you successfully do it. The first argument is frequency (in hertz, I believe), and the second should be time in milliseconds.
        else:
            print("You have too many moves. Would you like to replace one?")
            winsound.Beep(800, 300)     # This also does a chirp, but different
            
    
    def getLevel(self):
        T = self.level * 1000
        if self.XP >= T:
            self.Level +=1
            self.XP = 0
        winsound.Beep(2000, 250)
        return self.Level
    
    def displayHP(self):
        print (self.CurrentHP)
        winsound.Beep(2000, 250)
