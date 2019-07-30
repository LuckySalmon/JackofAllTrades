import random, winsound, moves

textWidth = 100
    
class Character:
    
    def __init__(self, Name, BaseHP, Speed, Defense, XP=0, moves=[]):
        self.Name = Name.title()
        self.BaseHP = BaseHP
        self.HP = BaseHP
        self.Speed = Speed
        self.Defense = Defense
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
            winsound.Beep(600, 125)
            winsound.Beep(750, 100)
            winsound.Beep(900, 150)
        else:
            print("You have too many moves. Would you like to replace one?")
            winsound.Beep(600, 175)
            winsound.Beep(500, 100)
            
    def updateLevel(self):
        threshold = self.Level * 1000
        while self.XP >= threshold:
            self.Level += 1
            self.XP -= threshold
            threshold = self.Level * 1000
        return self.Level
    
    def displayHP(self):
        print ("{}'s HP: {}".format(self.Name, self.HP).center(textWidth))

    #things we need:
    #various status affects

def align(*lines, side=0):
    functions = [lambda s: s, lambda s: s.center(textWidth), lambda s: s.rjust(textWidth)]
    l = []
    for line in lines:
        if type(line) in (list, tuple):
            s = ' '.join(line)
        else:
            s = str(line)
        l.append(functions[side](s) if s else '')
    return '\n'.join(l)

def chooseAttack(character, side):
    print(align('',
                'Select a move, %s:' %(character.Name),
                ('Availible Moves:', ', '.join(character.moveList)),
                "Or type a move followed by a '?' for more information",
                side=side))
    selection = input('').title()
    while not selection in character.moveList:
        if selection[-1] == '?' and selection[:-1].title() in character.moveList:
            character.moveList[selection[:-1].title()].showStats()
            selection = input('').title()
        else:
            selection = input(align('Please select a valid move.', '', side=side)).title()
    
    return selection

def battle(ally, enemy):
    print(align((ally.Name, " VS ", enemy.Name), side=1))
    for Character in (ally, enemy):
        Character.HP = Character.BaseHP
        Character.displayHP()
    characterList = [ally, enemy]
    characterList.sort(key= lambda char: char.Speed)
    characterList.reverse()
    i = 0
    while ally.HP > 0 and enemy.HP > 0:
        character = characterList[i]
        selection = chooseAttack(character, i*2)
        move = character.moveList[selection]
        success = move.getAccuracy() > random.randint(0, 99) # we should make this a set vaulue and use that to get predictable odds or change based on a dodege value from opposing character
                                                            #I have no idea what this^ means
        if success:
            damage = move.getDamage()
            print(align("{}'s {} hit for {} damage!".format(character.Name, selection, damage), side=1))
        else:
            damage = 0
            print(align("{}'s {} missed!".format(character.Name, selection), side=1))
        
        i = (i+1) % 2
        opponent = characterList[i]
        damage = min(max(damage - opponent.Defense, 0), opponent.HP)   #is this how defense is supposed to work?
        opponent.HP -= damage
        opponent.displayHP()
        print(align('{} took {} damage!'.format(opponent.Name, damage), side=1))
        
    for character in characterList:
        if character.HP > 0:
            print(align('', '%s wins!'%(character.Name), side=1))
        
def test():
    regular = Character('regular jack', 50, 1, 0, moves=moves.regularBasic)
    boxer = Character('boxer jack', 50, 2, 2, moves=moves.boxerBasic)
    psycho = Character('psycho jack', 40, 2, 1, moves=moves.psychoBasic)
    
    charList = {}
    for character in (regular, boxer, psycho):
        charList[character.Name[:-5].lower()] = character
    names = ['', '']
    for i, player in ((0, 'Player 1'), (1, 'Player 2')):
        name = input('%s Jack of choice: '%(player)).lower()
        while not name in charList:
            name = input('Please choose a valid character: ').lower()
        names[i] = name
    print('\n')
    battle(charList[names[0]], charList[names[1]])    
test()