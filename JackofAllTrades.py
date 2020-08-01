import csv
import json
import os

import characters
import graphics
import moves

textWidth = [100]


def display_health(character):
    """Print a character's health in a human-readable format."""
    print(align("{}'s HP: {}".format(character.Name, character.HP), side=1))


def align(*lines, side=0):
    """Format text such that it will appear aligned to a chosen side when printed."""
    functions = [lambda s1: s1, lambda s2: s2.center(textWidth[0]), lambda s3: s3.rjust(textWidth[0])]
    print_lines = []
    for line in lines:
        if type(line) in (list, tuple):
            s = ' '.join(line)
        else:
            s = str(line)
        print_lines.append(functions[side](s) if s else '')
    return '\n'.join(print_lines)


def choose_attack(character, side):
    """Ask a player to input a move and return it."""
    print(align('',
                'Select a move, %s:' % character.Name,
                ('Available Moves:', ', '.join(character.moveList)),
                "Or type a move followed by a '?' for more information",
                side=side))
    selection = input('').title()
    while selection not in character.moveList:
        if selection[-1] == '?' and selection[:-1].title() in character.moveList:
            character.moveList[selection[:-1].title()].show_stats()
            selection = input('').title()
        else:
            selection = input(align('Please select a valid move.', '', side=side)).title()

    return selection


def battle(ally, enemy):
    """Run a battle between Jacks."""
    print(align((ally.Name, " VS ", enemy.Name), side=1))
    for Character in (ally, enemy):
        Character.HP = Character.BaseHP
        display_health(Character)
    app = graphics.App([enemy, ally] if enemy.Speed > ally.Speed else [ally, enemy])
    app.run()


def test():
    """Have players choose Jacks, then run a game."""
    attribute_list = dict()
    move_sets = dict()
    for file in os.scandir('data\\characters'):
        with open(file) as f:
            d = json.load(f)
            trade = d['trade']
            move_sets[trade] = d.pop('basic_moves')
            attribute_list[trade] = d
    cont = input(align('Enter any character to play', 'Or nothing to quit', '', side=1))
    while cont:
        fighters = []
        for player in ('Player 1', 'Player 2'):
            for i in characters.charList:
                if i != "regular":  # this must be the first jack type
                    print(", ", end="")
                for j in i:
                    print(j, end="")
            print("\n")

            name = input('%s Jack of choice: ' % player).lower()
            while name not in characters.charList:
                name = input('Please choose a valid character: ').lower()

            move_set = move_sets[name] if name in move_sets else moves.defaultBasic
            fighters.append(characters.Character(attribute_list[name], char_moves=move_set))
        print('\n')
        battle(*fighters)
        cont = input(align('', 'Enter any character to play again', 'Or nothing to quit.', '', side=1))


def size_screen():
    """Ask user to set the width of their console so that text can be properly aligned."""
    alignment = '100'
    while alignment.isdigit():
        textWidth[0] = int(alignment)
        print(align('Left Side', side=0))
        print(align('Center', side=1))
        print(align('Right Side', side=2))
        alignment = input(
            'Type a number to set a new screen size (current is {}), or type a non-number to accept.\n'.format(
                alignment))


# size_screen()
graphics.test()
