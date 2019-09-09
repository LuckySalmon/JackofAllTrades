import random, moves, characters

textWidth = [100]

def displayHP(character):
        print(align("{}'s HP: {}".format(character.Name, character.HP), side=1))

def align(*lines, side=0):
    functions = [lambda s: s, lambda s: s.center(textWidth[0]), lambda s: s.rjust(textWidth[0])]
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
        displayHP(Character)
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
        print(align('{} took {} damage!'.format(opponent.Name, damage), side=1))
        displayHP(opponent)
        
    for character in characterList:
        if character.HP > 0:
            print(align('', '%s wins!'%(character.Name), side=1))
        
def test():
    cont = input(align('Enter any character to play', 'Or nothing to quit', '', side=1))
    while cont:
        fighters = []
        for player in ('Player 1', 'Player 2'):
            name = input('%s Jack of choice: '%(player)).lower()
            while not name in characters.charList:
                name = input('Please choose a valid character: ').lower()
            fighters.append(characters.charList[name]())
        print('\n')
        battle(*fighters)
        cont = input(align('', 'Enter any character to play again', 'Or nothing to quit.', '', side=1))

def sizeScreen():
    alignment = '100'
    while alignment.isdigit():
        textWidth[0] = int(alignment)
        print(align('Left Side', side=0))
        print(align('Center', side=1))
        print(align('Right Side', side=2))
        alignment = input('Type a number to set a new screen size (current is {}), or type a non-number to accept.\n'.format(alignment))

sizeScreen()
test()