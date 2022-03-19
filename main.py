import math
from itertools import product
from collections.abc import Iterable

from direct.showbase.MessengerGlobal import messenger
from direct.showbase.DirectObject import DirectObject
from direct.showbase.ShowBase import ShowBase
from direct.task.Task import Task
from panda3d.bullet import BulletDebugNode
from panda3d.core import Vec3
from direct.fsm.FSM import FSM

from characters import Character, Fighter, charList
from moves import Move
import physics
import ui

gravity = 0

DefaultTargetPos = (0.5, -0.25, 0)
LEFT, RIGHT = -1, 1
SIDES = (LEFT, RIGHT)

CHARACTERS = []
for char in charList:
    with open(f'data\\characters\\{char}.json') as f:
        CHARACTERS.append(Character.from_json(f))


class TargetMovingObject(DirectObject):
    def __init__(self, fighters):
        super().__init__()
        self.fighters = fighters
        self.xyz = (0, 0, 0)
        self.targets = []
        bindings = (('7-repeat', '1-repeat'), ('8-repeat', '2-repeat'), ('9-repeat', '3-repeat'))
        for axis, keys in enumerate(bindings):
            for i, key in enumerate(keys):
                self.accept(key, self.modify_coordinate, [axis, 0.01 * (-1)**i])
        self.accept('4-repeat', self.scale_targets, [0.99])
        self.accept('6-repeat', self.scale_targets, [1.01])
        self.accept('space', self.toggle_targeting)

    def update(self) -> None:
        x, y, z = self.xyz
        coordinates = [[x, y, z], [x, -y, z], [-x, -y, z], [-x, y, z]]
        self.targets = [Vec3(x, y, z) for x, y, z in coordinates]
        for (fighter, side), target in zip(product(self.fighters, SIDES), self.targets):
            fighter.skeleton.set_arm_target(side, Vec3(*target))

    def set_targets(self, x: float, y: float, z: float) -> None:
        self.xyz = [x, y, z]
        self.update()

    def modify_coordinate(self, axis: int, delta: float) -> None:
        self.xyz[axis] += delta
        self.update()

    def scale_targets(self, scale: float) -> None:
        for axis in range(3):
            self.xyz[axis] *= scale
        self.update()

    def toggle_targeting(self):
        for fighter in self.fighters:
            fighter.skeleton.toggle_targeting()


class ShoulderMovingObject(DirectObject):
    def __init__(self, character_list: list[Fighter]):
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

    def move_arms(self, axis: int, speed: float) -> None:
        for i, character in enumerate(self.character_list):
            character.skeleton.set_shoulder_motion(axis, speed)

    def bend_arms(self, angle: float) -> None:
        for character in self.character_list:
            for arm_controller in character.skeleton.arm_controllers.values():
                arm_controller.set_elbow_motion(angle, 0.5)

    def arms_down(self) -> None:
        for character in self.character_list:
            character.skeleton.arms_down()

    def print_angles(self) -> None:
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


class App(ShowBase, FSM):
    def __init__(self, fighters: list[Fighter] | None = None):
        ShowBase.__init__(self)
        FSM.__init__(self, 'GameFSM')

        self.fighters = []
        self.buttons = []
        self.index = 0

        self.world = None
        self.debugNP = None

        self.ui = None

        self.accept('main_menu', self.request, ['MainMenu'])
        self.accept('character_menu', self.request, ['CharacterMenu', 'Select a Character', CHARACTERS, 'view'])
        self.accept('fighter_selection', self.request, ['CharacterMenu', 'Select a Fighter', CHARACTERS])
        self.accept('select_character', self.select_character)
        self.accept('use_action', self.use_action)
        self.accept('next_turn', self.next_turn)
        self.accept('quit', self.userExit)

        self.main_menu = None
        self.character_menu = None

        if fighters is None:
            self.request('MainMenu')
        else:
            self.request('Battle', fighters)

    def enterMainMenu(self) -> None:
        self.fighters.clear()
        self.main_menu = ui.MainMenu()

    def exitMainMenu(self) -> None:
        if self.main_menu is not None:
            self.main_menu.hide()

    def enterCharacterMenu(self, title: str, character_list: Iterable[Character], mode: str) -> None:
        if mode == 'split_screen':
            title += ', Player 1'
        self.character_menu = ui.CharacterMenu(title, character_list, mode)

    def exitCharacterMenu(self) -> None:
        if self.character_menu is not None:
            self.character_menu.hide()

    def select_character(self, character: Character, mode: str) -> None:
        match mode:
            case 'split_screen':
                i = len(self.fighters)
                self.fighters.append(Fighter(character, i))
                if i == 0:
                    self.character_menu.title_text['text'] = 'Select a Fighter, Player 2'
                else:
                    self.request('Battle', self.fighters)
            case 'copy':
                fighters = [Fighter(character, i) for i in range(2)]
                self.request('Battle', fighters)

    def enterBattle(self, fighters: list[Fighter]) -> None:
        fighters.sort(key=lambda x: x.Speed, reverse=True)
        for fighter in fighters:
            fighter.HP = fighter.BaseHP
        self.fighters = fighters

        # Set up the World
        # The World
        self.world = physics.make_world(gravity)

        # Camera
        self.cam.setPos(0, -15, 2)
        self.cam.lookAt(0, 0, 0)

        # Characters
        fighters[0].insert(self.world, (-0.75, 0))
        fighters[1].insert(self.world, (0.75, 0))

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
        target_moving_object = TargetMovingObject(fighters)
        target_moving_object.set_targets(*DefaultTargetPos)
        for i in range(3):
            shoulder_moving_object.move_arms(i, 0)

        self.taskMgr.add(self.update, 'update')

        # Set up GUI
        self.ui = ui.BattleInterface(self.fighters)

        messenger.send('query_action', [0])

    def update(self, task: Task) -> int:
        """Update the world using physics."""
        return physics.update_physics(self.world, task)

    def toggle_debug(self) -> None:
        """Toggle debug display for physical objects."""
        if self.debugNP.isHidden():
            self.debugNP.show()
        else:
            self.debugNP.hide()

    def use_action(self, move: Move) -> None:
        """Make the character use the selected action, then move on to the next turn."""
        messenger.send('remove_query')
        user = self.fighters[self.index]

        self.index = (self.index + 1) % 2
        opponent = self.fighters[self.index]

        user.use_move(move, opponent, self.world)

    def next_turn(self):
        fighter = self.fighters[self.index]
        if fighter.HP <= 0:
            messenger.send('announce_win', [self.fighters[not self.index].Name])
        else:
            messenger.send('query_action', [self.index])


if __name__ == "__main__":
    app = App()
    app.run()
