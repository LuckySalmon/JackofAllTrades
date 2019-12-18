import random, moves, characters, graphics

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
                ('Available Moves:', ', '.join(character.moveList)),
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
    app = graphics.App([enemy, ally] if enemy.Speed > ally.Speed else [ally, enemy])
    app.run()
        
def test():
    cont = input(align('Enter any character to play', 'Or nothing to quit', '', side=1))
    while cont:
        fighters = []
        for player in ('Player 1', 'Player 2'):
            for i in characters.charList:
                if i != "regular": # this must be the first jack type
                        print (", ", end = "")
                for j in i:
                    print (j, end = "")
            print ("\n")
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
