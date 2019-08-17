import moves, winsound, csv
enableSound = True

class Character(object):
    
    def __init__(self, attributes, XP=0, moves=()):
        self.Name = attributes['Name']
        self.BaseHP = int(attributes['HP'])
        self.HP = int(attributes['HP'])
        self.Speed = int(attributes['Speed'])
        self.Defense = int(attributes['Defense'])
        self.XP = XP
        self.Level = 1
        self.updateLevel()
        self.moveList =  {}
        for move in moves:
            self.addMove(move)
        
    def moveList(self):    #isn't this redundant?
        '''check what moves this person has and return a list of availible moves'''
        print(self.moveList)
        return self.moveList

    def addMove(self, move):
        '''check that the only the correct number of moves is added to the list and give options to replace a move'''
        if len(self.moveList) < int(0.41 * self.Level +4):     #changed this from <= as I'm assuming the formula is meant to be a cap, not one less than the cap
            self.moveList[move.name] = move
            if enableSound:
                winsound.Beep(600, 125)
                winsound.Beep(750, 100)
                winsound.Beep(900, 150)
        else:
            print("You have too many moves. Would you like to replace one?")
            if enableSound:
                winsound.Beep(600, 175)
                winsound.Beep(500, 100)
            
    def updateLevel(self):
        threshold = self.Level * 1000
        while self.XP >= threshold:
            self.Level += 1
            self.XP -= threshold
            threshold = self.Level * 1000
        return self.Level

    #things we need:
    #various status affects

attributeList = {}
with open('characters.csv', newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        attributeList[row['Name'][:-5].lower()] = row

class default(Character):
    def __init__(self, XP=0):
        super().__init__(attributeList['regular'], moves=moves.defaultBasic, XP=XP)

class boxer(Character):
    def __init__(self, XP=0):
        super().__init__(attributeList['boxer'], moves=moves.boxerBasic, XP=XP)

class psycho(Character):
    def __init__(self, XP=0):
        super().__init__(attributeList['psycho'], moves=moves.psychoBasic, XP=XP)

class testChar(Character):
    def __init__(self, XP=0):
        super().__init__(attributeList['test'], moves=moves.defaultBasic, XP=XP)

charList = dict(regular=default, boxer=boxer, psycho=psycho, test=testChar)