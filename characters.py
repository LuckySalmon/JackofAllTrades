import csv
import moves
import winsound

enableSound = True


def char_init(self, attributes, XP=0, moves=()):
    self.Name = attributes['name'].title()
    self.BaseHP = int(attributes['hp'])
    self.HP = int(attributes['hp'])
    self.Speed = int(attributes['speed'])
    self.Defense = int(attributes['defense'])
    self.XP = XP
    self.Level = 1
    self.updateLevel()
    self.moveList = {}
    for move in moves:
        self.addMove(move)


class Character(object):
    __init__ = char_init

    def moveList(self):  # isn't this redundant?
        '''check what moves this person has and return a list of availible moves'''
        print(self.moveList)
        return self.moveList

    def addMove(self, move):
        '''check that the only the correct number of moves is added to the list and give options to replace a move'''
        if len(self.moveList) < int(
                0.41 * self.Level + 4):  # changed this from <= as I'm assuming the formula is meant to be a cap, not one less than the cap
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

    # things we need:
    # various status affects


attributeList = {}
with open('characters.csv', newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        attributeList[row['name'][:-5]] = row

charList = {}


def create_class(name, attributes, l):
    set_name = name + ' basic'
    move_set = moves.sets[set_name] if set_name in moves.sets else moves.defaultBasic
    l[name] = type(name, (Character,), {'__init__': lambda self: char_init(self, attributes, moves=move_set)})


for name in attributeList:
    create_class(name, attributeList[name], charList)
