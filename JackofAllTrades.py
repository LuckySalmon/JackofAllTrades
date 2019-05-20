import random

# The class "Moves" should be entirely self sufficient and not require any numbers or
#variables outside of the class.


class Move:
    def __init__(self, name, dmg, acc, status=''):
        self.name = name.title()
        self.dmg = dmg
        self.acc = acc
        self.status = status

    def getDamage(self):
        return random.randint(*self.dmg)
    
    def getAccuracy(self):
        return random.randint(*self.acc)     #does accuracy really need to be a range? (if I'm right and it's the chance of the attack hitting)
    
    def getStatus(self):
        return status
    
    def use(self):
        success = self.getAccuracy() > random.randint(0, 99) # we should make this a set vaulue and use that to get predictable odds or change based on a dodege value from opposing character
        damage = self.getDamage() if success else 0
        return success, damage

 
class Character:
    def __init__(self, Name, BaseHP, Speed, Defence, XP):
        self.Name = Name.title()
        self.BaseHP = BaseHP
        self.HP = BaseHP
        self.Speed = Speed
        self.Defence = Defence
        self.XP = XP
        self.moveList = {}
        self.Level = 1
        
    def moveList(self):
        '''check what moves this character has and return a list of availible moves'''
        print(self.moveList)

    def addMove(self, move):
        '''check that only the correct number of moves is added to the list and give options to replace a move'''
        if len(self.moveList) <= int(0.41 * self.Level +4):
            self.moveList[move.name] = move
        else:

            print("You have too many moves would you like to replace one?")
    
    def getLevel(self):
        T = self.level * 1000
        if self.XP >= T:
            self.Level +=1
            self.XP = 0

            print("You have too many moves. Would you like to replace one?")
            
    def updateLevel(self):
        threshold = self.level * 1000
        while self.XP >= threshold:
            self.Level += 1
            self.XP -= threshold
            threshold = self.level * 1000

        return self.Level
    
    def displayHP(self):
        print (self.Name + "'s HP:", self.HP)


    #things we need
        #take dammage , use moves, die, various status affects, 

def battle(ally, enemy):
    print(ally.Name, " VS ", enemy.Name)
    
    for Character in (ally, enemy):
        Character.HP = Character.BaseHP
        Character.displayHP()

    while ally.HP > 0 and enemy.HP > 0:
        if ally.Speed > enemy.Speed:
            print('Select a move %s:' %(ally.Name))
            for move in ally.moveList:
                print(move)
                dmg = ally.moveList[move].dmg
                acc = ally.moveList[move].acc
                print('\tDamage:', dmg[0], '-', dmg[1])
                print('\tAccuracy:', acc[0], '-', acc[1])
            selection = input('').title()
            
            while not selection in ally.moveList:
                selection = input('Please select a valid move.\n').title()
            result = ally.moveList[selection].use()
            
            if result[0]:
                print(ally.Name + "'s", selection, 'hit for', result[1], 'damage!')
            else:
                print(ally.Name + "'s", selection, 'missed!')
            enemy.HP -= result[1]
            enemy.displayHP()
#2nd
            print('Select a move %s:' %(enemy.Name))
            for move in enemy.moveList:
                print(move)
                dmg = enemy.moveList[move].dmg
                acc = enemy.moveList[move].acc
                print('\tDamage:', dmg[0], '-', dmg[1])
                print('\tAccuracy:', acc[0], '-', acc[1])
            selection = input('').title()
            
            while not selection in ally.moveList:
                selection = input('Please select a valid move.\n').title()
            result = enemy.moveList[selection].use()
            
            if result[0]:
                print(enemy.Name + "'s", selection, 'hit for', result[1], 'damage!')
            else:
                print(enemy.Name + "'s", selection, 'missed!')
            ally.HP -= result[1]
            ally.displayHP()

        
        
def test():
    flick = Move('flick', (0, 1), (100, 100))
    punch = Move('punch', (5, 15), (80, 95))
    spit = Move('spit', (0, 0), (40, 60), 'gross')
    one = Character('one', 100, 2, 1, 1)
    two = Character('two', 100, 1
                    , 2, 2)
    
    for character in (one, two):
        for move in (flick, punch, spit):
            character.addMove(move)
    battle(one, two)

