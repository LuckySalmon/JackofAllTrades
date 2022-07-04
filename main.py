from itertools import product
from collections.abc import Iterable

from direct.showbase.MessengerGlobal import messenger
from direct.showbase.DirectObject import DirectObject
from direct.showbase.ShowBase import ShowBase
from direct.task.Task import Task
from panda3d.bullet import BulletDebugNode, BulletWorld
from panda3d.core import NodePath, Vec3
from direct.fsm.FSM import FSM

from characters import Character, Fighter
from moves import Move
import physics
import ui

gravity = 0

DefaultTargetPos = (0.5, -0.25, 0)
LEFT, RIGHT = -1, 1
SIDES = (LEFT, RIGHT)

CHARACTERS = []
for name in ('regular', 'boxer', 'psycho', 'test'):
    with open(f'data\\characters\\{name}.json') as f:
        CHARACTERS.append(Character.from_json(f))


class TargetMovingObject(DirectObject):
    fighters: Iterable[Fighter]
    xyz: list[float]
    targets: list[Vec3]

    def __init__(self, fighters: Iterable[Fighter]):
        super().__init__()
        self.fighters = fighters
        self.xyz = [0, 0, 0]
        self.targets = []
        bindings = (('7-repeat', '1-repeat'),
                    ('8-repeat', '2-repeat'),
                    ('9-repeat', '3-repeat'))
        for axis, keys in enumerate(bindings):
            for i, key in enumerate(keys):
                self.accept(key, self.modify_coordinate,
                            [axis, 0.01 * (-1) ** i])
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


class GameFSM(FSM):
    app: 'App'
    fighters: list[Fighter]
    main_menu: ui.MainMenu | None
    character_menu: ui.CharacterMenu | None
    battle_interface: ui.BattleInterface | None

    def __init__(self, app: 'App'):
        FSM.__init__(self, 'GameFSM')
        self.app = app
        self.fighters = self.app.fighters
        self.main_menu = None
        self.character_menu = None
        self.battle_interface = None

    def enterMainMenu(self) -> None:
        self.fighters.clear()
        if self.main_menu is not None:
            self.main_menu.show()
        else:
            self.main_menu = ui.MainMenu()

    def exitMainMenu(self) -> None:
        if self.main_menu is not None:
            self.main_menu.hide()

    def enterCharacterMenu(self, title: str,
                           character_list: Iterable[Character],
                           mode: str) -> None:
        if mode == 'split_screen':
            title += ', Player 1'
        if self.character_menu is not None:
            self.character_menu.show()
        else:
            self.character_menu = ui.CharacterMenu(title, character_list, mode)

    def exitCharacterMenu(self) -> None:
        if self.character_menu is not None:
            self.character_menu.hide()

    def enterBattle(self, characters: list[Character]) -> None:
        self.app.enter_battle(characters)
        self.battle_interface = ui.BattleInterface(self.fighters)
        messenger.send('query_action', [0])


class App(ShowBase):
    fighters: list[Fighter]
    fsm: GameFSM
    selected_characters: list[Character]
    index: int
    world: BulletWorld | None
    debugNP: 'NodePath[BulletDebugNode]'

    def __init__(self):
        ShowBase.__init__(self)
        self.fighters = []
        self.fsm = GameFSM(self)

        self.selected_characters = []
        self.index = 0

        self.world = None
        self.debugNP = None

        self.accept('main_menu', self.request, ['MainMenu'])
        self.accept('character_menu', self.request,
                    ['CharacterMenu', 'Select a Character', CHARACTERS, 'view'])
        self.accept('fighter_selection', self.request,
                    ['CharacterMenu', 'Select a Fighter', CHARACTERS])
        self.accept('select_character', self.select_character)
        self.accept('use_action', self.use_action)
        self.accept('next_turn', self.next_turn)
        self.accept('quit', self.userExit)

        self.request('MainMenu')

    def request(self, request: str, *args) -> None:
        self.fsm.request(request, *args)

    def select_character(self, character: Character, mode: str) -> None:
        match mode:
            case 'split_screen':
                i = len(self.selected_characters)
                self.selected_characters.append(character)
                if i == 0:
                    self.fsm.character_menu.title_text['text'] = 'Select a Fighter, Player 2'
                else:
                    self.request('Battle', self.selected_characters)
            case 'copy':
                self.request('Battle', [character, character])

    def enter_battle(self, characters: list[Character]) -> None:
        # Set up the World
        self.world = physics.make_world(gravity)
        self.cam.setPos(0, -15, 2)
        self.cam.lookAt(0, 0, 0)

        # Fighters
        self.fighters.clear()
        for i, character in enumerate(characters):
            fighter = Fighter.from_character(character, self.world, i)
            fighter.hp = fighter.base_hp
            self.fighters.append(fighter)
        self.fighters.sort(key=lambda x: x.speed, reverse=True)

        # Debug
        debug_node = BulletDebugNode('Debug')
        debug_node.showConstraints(False)
        self.debugNP = self.render.attachNewNode(debug_node)
        self.debugNP.show()
        self.world.setDebugNode(debug_node)
        debug_object = DirectObject()
        debug_object.accept('f1', self.toggle_debug)

        # Arm Control
        target_moving_object = TargetMovingObject(self.fighters)
        target_moving_object.set_targets(*DefaultTargetPos)

        self.taskMgr.add(self.update, 'update')

    def update(self, task: Task) -> int:
        """Update the world using physics."""
        return physics.update_physics(self.world, task)

    def toggle_debug(self) -> None:
        """Toggle debug display for physical objects."""
        if self.debugNP.isHidden():
            self.debugNP.show()
        else:
            self.debugNP.hide()

    def use_action(self, move: Move, target_index: int) -> None:
        """Make the character use the selected action,
        then move on to the next turn.
        """
        messenger.send('remove_query')
        user = self.fighters[self.index]
        self.index = (self.index + 1) % 2
        user.use_move(move, self.fighters[target_index], self.world)

    def next_turn(self):
        fighter = self.fighters[self.index]
        fighter.apply_current_effects()
        if fighter.hp <= 0:
            messenger.send('announce_win', [self.fighters[not self.index].name])
        else:
            messenger.send('query_action', [self.index])


def main() -> None:
    """Run an instance of the app."""
    app = App()
    app.run()


if __name__ == "__main__":
    main()
