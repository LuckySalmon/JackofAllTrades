from __future__ import annotations

from collections.abc import Iterable
from itertools import product
from pathlib import Path
from typing import Any

from direct.fsm.FSM import FSM
from direct.showbase.DirectObject import DirectObject
from direct.showbase.MessengerGlobal import messenger
from direct.showbase.ShowBase import ShowBase
from direct.task.Task import Task
from panda3d.bullet import BulletDebugNode, BulletWorld
from panda3d.core import NodePath, Vec3

from . import physics, ui
from .characters import Character, Fighter
from .moves import Move
from .skeletons import Skeleton

gravity = 0
LEFT, RIGHT = -1, 1
CHARACTERS: list[Character] = []


class TargetMovingObject(DirectObject):
    skeletons: tuple[Skeleton, ...]
    xyz: Vec3

    def __init__(self, skeletons: Iterable[Skeleton]) -> None:
        super().__init__()
        self.skeletons = tuple(skeletons)
        self.xyz = Vec3(0.5, -0.25, 0)
        d = 0.01
        self.accept('7-repeat', self.add_to_target, [Vec3(+d, 0, 0)])
        self.accept('1-repeat', self.add_to_target, [Vec3(-d, 0, 0)])
        self.accept('8-repeat', self.add_to_target, [Vec3(0, +d, 0)])
        self.accept('2-repeat', self.add_to_target, [Vec3(0, -d, 0)])
        self.accept('9-repeat', self.add_to_target, [Vec3(0, 0, +d)])
        self.accept('3-repeat', self.add_to_target, [Vec3(0, 0, -d)])
        self.accept('4-repeat', self.add_to_target, [Vec3(-d, -d, -d)])
        self.accept('6-repeat', self.add_to_target, [Vec3(+d, +d, +d)])
        self.accept('space', self.toggle_targeting)
        self.update()

    def update(self) -> None:
        x, y, z = self.xyz
        targets = (Vec3(+x, +y, z), Vec3(+x, -y, z),
                   Vec3(-x, -y, z), Vec3(-x, +y, z))
        iterator = zip(product(self.skeletons, (LEFT, RIGHT)), targets)
        for (skel, side), target in iterator:
            skel.set_arm_target(side, target)

    def add_to_target(self, delta: Vec3) -> None:
        self.xyz += delta
        self.update()

    def toggle_targeting(self) -> None:
        for skel in self.skeletons:
            skel.toggle_targeting()


class GameFSM(FSM):
    app: App
    fighters: list[Fighter]
    main_menu: ui.MainMenu | None
    character_menu: ui.CharacterMenu | None
    battle_interface: ui.BattleInterface | None

    def __init__(self, app: App) -> None:
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
                           characters: Iterable[Character],
                           mode: str) -> None:
        if mode == 'split_screen':
            title += ', Player 1'
        if self.character_menu is not None:
            self.character_menu.reset(characters, mode)
            self.character_menu.show()
        else:
            self.character_menu = ui.CharacterMenu(title, characters, mode)

    def exitCharacterMenu(self) -> None:
        if self.character_menu is not None:
            self.character_menu.hide()

    def enterBattle(self, characters: Iterable[Character]) -> None:
        self.app.enter_battle(characters)
        self.battle_interface = ui.BattleInterface(self.fighters)
        messenger.send('query_action', [0])


class App(ShowBase):
    fighters: list[Fighter]
    fsm: GameFSM
    selected_characters: list[Character]
    index: int
    world: BulletWorld | None
    debugNP: NodePath[BulletDebugNode] | None

    def __init__(self) -> None:
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

    def request(self, request: str, *args: Any) -> None:
        self.fsm.request(request, *args)

    def select_character(self, character: Character, mode: str) -> None:
        assert self.fsm.character_menu is not None
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

    def enter_battle(self, characters: Iterable[Character]) -> None:
        # Set up the World
        self.world = physics.make_world(gravity)
        self.cam.set_pos(0, -15, 2)
        self.cam.look_at(0, 0, 0)

        # Fighters
        self.fighters.clear()
        for i, character in enumerate(characters):
            fighter = Fighter.from_character(character, self.world, i)
            fighter.hp = fighter.base_hp
            self.fighters.append(fighter)
        self.fighters.sort(key=lambda x: x.speed, reverse=True)

        # Debug
        debug_node = BulletDebugNode('Debug')
        debug_node.show_constraints(False)
        self.debugNP = self.render.attach_new_node(debug_node)
        self.debugNP.show()
        self.world.set_debug_node(debug_node)
        debug_object = DirectObject()
        debug_object.accept('f1', self.toggle_debug)

        # Arm Control
        TargetMovingObject(fighter.skeleton for fighter in self.fighters)

        self.taskMgr.add(self.update, 'update')

    def update(self, task: Task) -> int:
        """Update the world using physics."""
        assert self.world is not None
        return physics.update_physics(self.world, task)

    def toggle_debug(self) -> None:
        """Toggle debug display for physical objects."""
        assert self.debugNP is not None
        if self.debugNP.is_hidden():
            self.debugNP.show()
        else:
            self.debugNP.hide()

    def use_action(self, move: Move, target_index: int) -> None:
        """Make the character use the selected action,
        then move on to the next turn.
        """
        assert self.world is not None
        messenger.send('remove_query')
        user = self.fighters[self.index]
        self.index = (self.index + 1) % 2
        user.use_move(move, self.fighters[target_index], self.world)

    def next_turn(self) -> None:
        fighter = self.fighters[self.index]
        fighter.apply_current_effects()
        if fighter.hp <= 0:
            messenger.send('announce_win', [self.fighters[not self.index].name])
        else:
            messenger.send('query_action', [self.index])


def main() -> None:
    """Run an instance of the app."""
    for fp in Path('data', 'characters').iterdir():
        with fp.open() as f:
            CHARACTERS.append(Character.from_json(f))
    app = App()
    app.run()
