import random, winsound, moves
    
class Character:
    
    def __init__(self, Name, BaseHP, Speed, Defense, XP=0):
        self.Name = Name.title()
        self.BaseHP = BaseHP
        self.HP = BaseHP
        self.Speed = Speed
        self.Defense = Defense
        self.moveList =  {}
        self.XP = XP
        self.Level = 1
        
    def moveList(self):    #isn't this redundant?
        '''check what moves this person has and return a list of availible moves'''
        print(self.moveList)
        return self.moveList

    def addMove(self, move):
        '''check that the only the correct number of moves is added to the list and give options to replace a move'''
        if len(self.moveList) < int(0.41 * self.Level +4):     #changed this from <= as I'm assuming the formula is meant to be a cap, not one less than the cap
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
    #various status affects, 

def battle(ally, enemy):
    print(ally.Name, " VS ", enemy.Name)
    
    for Character in (ally, enemy):
        Character.HP = Character.BaseHP
        Character.displayHP()
    characterList = [ally, enemy]
    characterList.sort(key= lambda char: char.Speed)
    characterList.reverse()
    i = 0
    
    while ally.HP > 0 and enemy.HP > 0:
        character = characterList[i]
        print('\nSelect a move, %s:' %(character.Name))
        moveListString = 'Availible Moves: '
        for move in character.moveList:
            moveListString += move + ', '
        print(moveListString[:-2])
        print("Or type a move followed by a '?' for more information")
        selection = input('').title()
        
        while not selection in character.moveList:
            if selection[-1] == '?' and selection[:-1].title() in character.moveList:
                character.moveList[selection[:-1].title()].showStats()
                selection = input('').title()
            else:
                selection = input('Please select a valid move.\n').title()
        result = character.moveList[selection].use()
        
        if result[0]:
            print(character.Name + "'s", selection, 'hit for', result[1], 'damage!')
        else:
            print(character.Name + "'s", selection, 'missed!')
        
        i = (i+1) % 2
        opponent = characterList[i]
        damage = min(max(result[1] - opponent.Defense, 0), opponent.HP)   #is this how defense is supposed to work?
        opponent.HP -= damage
        print(opponent.Name, 'took', damage, 'damage!')
        opponent.displayHP()
        
    for character in characterList:
        if character.HP > 0:
            print('\n' + character.Name, 'wins!')
        
def test():
    one = Character('one', 25, 1, 1, 1)
    two = Character('two', 25, 2, 2, 2)
    
    boxer = Character('boxer jack', 50, 2, 2)
    boxer.addMove(moves.jab)
    boxer.addMove(moves.cross)
    boxer.addMove(moves.hook)
    knife = Character('knife jack', 40, 2, 1)
    knife.addMove(moves.shank)
    knife.addMove(moves.stab)
    knife.addMove(moves.slice)
    
    for character in (one, two):
        for move in (moves.flick, moves.punch, moves.spit):
            character.addMove(move)
    battle(one, two)