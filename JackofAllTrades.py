import random, winsound

# The class "Move" should be entirely self sufficient, and not require any numbers or variables outside of the class.


class Move:
    def __init__(self, name, dmg, acc, status=''):
        self.name = name.title()
        self.dmg = dmg
        self.acc = acc
        self.status = status

    def getDamage(self):
        return random.randint(*self.dmg)
    
    def getAccuracy(self):
        return self.acc
    
    def getStatus(self):
        return self.status
    
    def use(self):
        success = self.getAccuracy() > random.randint(0, 99) # we should make this a set vaulue and use that to get predictable odds or change based on a dodege value from opposing character
        damage = self.getDamage() if success else 0
        return success, damage

    
class Character:
    
    def __init__(self, Name, BaseHP, Speed, Defense, XP):
        self.Name = Name.title()
        self.BaseHP = BaseHP
        self.HP = BaseHP
        self.Speed = Speed
        self.Defense = Defense
        self.XP = XP
        self.moveList =  {}
        self.Level = 1
        
    def moveList(self):
        '''check what moves this person has and return a list of availible moves'''
        print(self.moveList)
        return self.moveList

    def addMove(self, move):
        '''check that the only the correct number of moves is added to the list and give options to replace a move'''
        if len(self.moveList) <= int(0.41 * self.Level +4):
            self.moveList[move.name] = move
            winsound.Beep(600, 125)
            winsound.Beep(750, 100)
            winsound.Beep(900, 150)
        else:
            print("You have too many moves. Would you like to replace one?")
            winsound.Beep(600, 175)
            winsound.Beep(500, 100)
            
    def updateLevel(self):
        threshold = self.level * 1000
        while self.XP >= threshold:
            self.Level += 1
            self.XP -= threshold
            threshold = self.level * 1000
        return self.Level
    
    def displayHP(self):
        print (self.Name + "'s HP:", self.HP)

    #things we need:
    #take dammage , use moves, die, various status affects, 

def battle(ally, enemy):
    print(ally.Name, " VS ", enemy.Name)
    
    for Character in (ally, enemy):
        Character.HP = Character.BaseHP
        Character.displayHP()
    characterList = [ally, enemy]
    characterList.sort(key= lambda char: char.Speed)
    characterList.reverse()
    while ally.HP > 0 and enemy.HP > 0:
        for i, character in enumerate(characterList):
            print('Select a move, %s:' %(character.Name))
            for move in character.moveList:
                print(move)
                dmg = character.moveList[move].dmg
                acc = character.moveList[move].acc
                print('\tDamage:', dmg[0], '-', dmg[1])
                print('\tAccuracy:', str(acc) + '%')
            selection = input('').title()
            
            while not selection in character.moveList:
                selection = input('Please select a valid move.\n').title()
            result = character.moveList[selection].use()
            
            if result[0]:
                print(character.Name + "'s", selection, 'hit for', result[1], 'damage!')
            else:
                print(character.Name + "'s", selection, 'missed!')
            opponent = characterList[(i+1)%2]
            opponent.HP -= result[1]
            opponent.displayHP()
        
def test():
    flick = Move('flick', (0, 1), 100)
    punch = Move('punch', (5, 15), 90)
    spit = Move('spit', (0, 0), 55, 'gross')
    one = Character('one', 25, 1, 1, 1)
    two = Character('two', 25, 2, 2, 2)
    
    for character in (one, two):
        for move in (flick, punch, spit):
            character.addMove(move)
    battle(one, two)
