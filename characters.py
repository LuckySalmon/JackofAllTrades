import csv
import moves
import winsound

enableSound = True


def char_init(self, attributes, xp=0, char_moves=()):
    """Set up a character class."""
    self.Name = attributes['name'].title()
    self.BaseHP = int(attributes['hp'])
    self.HP = int(attributes['hp'])
    self.Speed = int(attributes['speed'])
    self.Defense = int(attributes['defense'])
    self.XP = xp
    self.Level = 1
    self.update_level()
    self.moveList = {}
    for move in char_moves:
        self.add_move(move)


class Character(object):
    def list_moves(self):  # isn't this redundant?
        """Check what moves this character has and return a list of available moves."""
        print(self.moveList)
        return self.moveList

    def add_move(self, move):
        """Attempt to add a move to this list of those available."""
        if len(self.moveList) < int(0.41 * self.Level + 4):
            # changed the above from <= as I'm assuming the formula is meant to be a cap, not one less than the cap
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

    def update_level(self):
        """Use a character's XP to increase their level."""
        while self.XP >= (threshold := self.Level * 1000):
            self.Level += 1
            self.XP -= threshold
        return self.Level

    # TODO: create various status affects


attributeList = {}
with open('characters.csv', newline='') as file:
    for row in (reader := csv.DictReader(file)):
        attributeList[row['name'][:-5]] = row

charList = {}


def create_class(name, attributes, char_list):
    """Insert a character into the list of those available."""
    set_name = name + ' basic'
    move_set = moves.sets[set_name] if set_name in moves.sets else moves.defaultBasic
    char_list[name] = type(name, (Character,), {'__init__': lambda self: char_init(self, attributes, char_moves=move_set)})


for class_name in attributeList:
    create_class(class_name, attributeList[class_name], charList)
