import math
import random
from itertools import product

from direct.showbase.DirectObject import DirectObject
from direct.showbase.ShowBase import ShowBase
from panda3d.bullet import BulletDebugNode
from panda3d.core import Vec3

import characters
import physics
import ui

gravity = 0

sides = ['l', 'r']
DefaultTargetPos = (1, 1, 0)
TARGETING = [False]
LEFT, RIGHT = -1, 1

CHARACTERS = []
for char in characters.charList:
    with open(f'data\\characters\\{char}.json') as f:
        CHARACTERS.append(characters.Character.from_json(f))


def toggle_targeting():
    TARGETING[0] = not TARGETING[0]


class TargetMovingObject(DirectObject):
    def __init__(self):
        super().__init__()
        self.xyz = (0, 0, 0)
        self.targets = []
        bindings = (('7-repeat', '1-repeat'), ('8-repeat', '2-repeat'), ('9-repeat', '3-repeat'))
        for axis, keys in enumerate(bindings):
            for i, key in enumerate(keys):
                self.accept(key, self.modify_coordinate, [axis, 0.01 * (-1)**i])
        self.accept('4-repeat', self.scale_targets, [0.99])
        self.accept('6-repeat', self.scale_targets, [1.01])

    def update(self):
        x, y, z = self.xyz
        coordinates = [[x, y, z], [x, -y, z], [-x, -y, z], [-x, y, z]]
        self.targets.clear()
        targets = [Vec3(x, y, z) for x, y, z in coordinates]
        self.targets += targets

    def set_targets(self, x, y, z):
        self.xyz = [x, y, z]
        self.update()
        return self.targets

    def modify_coordinate(self, axis, delta):
        self.xyz[axis] += delta
        self.update()

    def scale_targets(self, scale):
        for axis in range(3):
            self.xyz[axis] *= scale
        self.update()


class ShoulderMovingObject(DirectObject):
    def __init__(self, character_list):
        super().__init__()
        self.character_list = character_list
        bindings = [('q', 'e'), ('a', 'd'), ('z', 'c')]
        for axis, keys in enumerate(bindings):
            for i, key in enumerate(keys):
                self.accept(key, self.move_arms, [axis, (-1) ** i])
                self.accept(key + '-up', self.move_arms, [axis, 0])
        self.accept('s', self.arms_down)
        self.accept('r', self.bend_arms, [math.pi / 2])
        self.accept('v', self.bend_arms, [0.0])
        self.accept('p', self.print_angles)
        self.accept('space', toggle_targeting)

    def move_arms(self, axis, speed):
        for i, character in enumerate(self.character_list):
            character.skeleton.set_shoulder_motion(axis, speed)

    def bend_arms(self, angle):
        for character in self.character_list:
            for arm in character.skeleton.arm_l, character.skeleton.arm_r:
                arm.elbow.enableMotor(True)
                arm.elbow.setMotorTarget(angle, 0.5)
                arm.forearm.node().setActive(True, False)

    def arms_down(self):
        for character in self.character_list:
            character.skeleton.arms_down()

    def print_angles(self):
        for character in self.character_list:
            for arm in character.skeleton.arm_l, character.skeleton.arm_r:
                angles = [arm.shoulder.getAngle(i) for i in range(3)]
                print('angles: {:.4f}, {:.4f}, {:.4f}'.format(*angles))
                angles[2] *= -1
                c3, c2, c1 = [math.cos(angle) for angle in angles]
                s3, s2, s1 = [math.sin(angle) for angle in angles]
                calculated_point = Vec3(c1 * c3 * s2 + s1 * s3, -c2 * c3, -c1 * s3 + c3 * s1 * s2) * 0.375
                print('calculated bicep pos: ({: .4f}, {: .4f}, {: .4f})'.format(*calculated_point))
                actual_point = arm.bicep.getPos() - arm.position
                print('    actual bicep pos: ({: .4f}, {: .4f}, {: .4f})'.format(*actual_point))
                print()


class App(ShowBase):
    def __init__(self, fighters=None):
        super().__init__(self)

        self.clock = 0

        self.fighters = []
        self.buttons = []
        self.index = 0

        self.world = None
        self.debugNP = None

        self.targets = []

        self.ui = None
        self.selectedAction, self.selection = None, None

        self.accept('fighter_selection', self.select_fighter, [CHARACTERS])
        self.accept('set_fighter', self.set_fighter)
        self.accept('set_action', self.set_action)
        self.accept('use_action', self.use_action)
        self.accept('quit', self.userExit)

        self.fighter_selection = None
        if fighters is None:
            self.menu = ui.MainMenu()
        else:
            self.menu = None
            self.start_battle(fighters)

    def select_fighter(self, character_list, mode):
        if self.menu is not None:
            self.menu.hide()
        self.fighter_selection = ui.FighterSelectionMenu('Select Fighter', character_list, mode)

    def set_fighter(self, character, mode):
        match mode:
            case 'split_screen':
                self.fighters.append(characters.Fighter(character))
                if len(self.fighters) > 1:
                    self.start_battle(self.fighters)
            case 'copy':
                fighters = [characters.Fighter(character) for _ in range(2)]
                self.start_battle(fighters)

    def start_battle(self, fighters):
        if self.fighter_selection is not None:
            self.fighter_selection.hide()

        fighters.sort(key=lambda x: x.Speed, reverse=True)
        for fighter in fighters:
            fighter.HP = fighter.BaseHP
        self.fighters = fighters

        # Set up the World
        # The World
        self.world = physics.make_world(gravity, self.render)

        # Camera
        self.cam.setPos(0, -15, 2)
        self.cam.lookAt(0, 0, 0)

        # Characters
        fighters[0].insert(self.world, self.render, -1, (-2, 0))
        fighters[1].insert(self.world, self.render, 1, (2, 0))

        # Debug
        debug_node = BulletDebugNode('Debug')
        debug_node.showWireframe(True)
        debug_node.showConstraints(False)
        debug_node.showBoundingBoxes(False)
        debug_node.showNormals(False)
        self.debugNP = self.render.attachNewNode(debug_node)
        self.debugNP.show()
        self.world.setDebugNode(self.debugNP.node())
        debug_object = DirectObject()
        debug_object.accept('f1', self.toggle_debug)

        # Testing Controls
        shoulder_moving_object = ShoulderMovingObject(fighters)
        target_moving_object = TargetMovingObject()
        self.targets = target_moving_object.set_targets(*DefaultTargetPos)
        for i in range(3):
            shoulder_moving_object.move_arms(i, 0)

        self.taskMgr.add(self.update, 'update')

        # Set up GUI
        self.ui = ui.BattleInterface(self.fighters)

        self.query_action()

    def update(self, task):
        """Update the world using physics."""
        self.clock += 1
        if TARGETING[0] and self.clock % 10 == 0:
            for (fighter, side), target in zip(product(self.fighters, sides), self.targets):
                fighter.skeleton.position_shoulder(side, target)
        return physics.update_physics(self.world, task)

    def toggle_debug(self):
        """Toggle debug display for physical objects."""
        if self.debugNP.isHidden():
            self.debugNP.show()
        else:
            self.debugNP.hide()

    def query_action(self):
        """Set up buttons for a player to choose an action."""
        fighter = self.fighters[self.index]
        self.ui.query_action(fighter, self.index)

    def set_action(self, fighter, name):
        """Set an action to be selected."""
        i = self.index
        self.selectedAction = fighter.moveList[name]
        self.ui.output_info(i, self.selectedAction.show_stats())
        self.ui.select_action(i, name)
        self.selection = name

    def use_action(self):
        """Make the character use the selected action, then move on to the next turn."""
        self.ui.remove_query()
        user = self.fighters[self.index]
        name, move = self.selection, self.selectedAction

        # Result of move
        if move.get_accuracy() > random.randint(0, 99):
            damage = move.get_damage()
            if random.randint(1, 100) <= 2:
                damage *= 1.5
                print("Critical Hit!".format(user.Name, name, damage))
            self.ui.output_info(self.index, f"{user.Name}'s {name} hit for {damage} damage!")
        else:
            damage = 0
            self.ui.output_info(self.index, f"{user.Name}'s {name} missed!")

        # Move over to other character and apply damage
        self.index = (self.index + 1) % 2
        opponent = self.fighters[self.index]
        damage = min(max(damage - opponent.Defense, 0), opponent.HP)  # TODO: Find and use a better formula
        opponent.HP -= damage
        self.ui.apply_damage(self.index, damage, opponent.Name)

        # Move on to next step (KO or opponent response)
        if opponent.HP <= 0:
            self.ui.announce_win(user.Name)
            # I thought this would make the character fall, but it just glitches out
            self.fighters[self.index].skeleton.torso.node().setMass(1.0)
            self.fighters[self.index].skeleton.torso.node().setActive(True, False)
        else:
            self.query_action()


if __name__ == "__main__":
    app = App()
    app.run()
