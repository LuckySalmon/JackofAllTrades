from __future__ import annotations

import logging
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Final

from direct.fsm.FSM import FSM
from direct.showbase.DirectObject import DirectObject
from direct.showbase.MessengerGlobal import messenger
from direct.showbase.ShowBase import ShowBase
from direct.task.Task import Task
from panda3d.bullet import BulletDebugNode, BulletWorld
from panda3d.core import NodePath, Vec3

from . import physics, stances, ui
from .characters import Character, Fighter
from .moves import Move

_logger: Final = logging.getLogger(__name__)

GRAVITY: Final = Vec3(0, 0, -9.81)


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

    def enterCharacterMenu(
        self, title: str, characters: Iterable[Character], mode: str
    ) -> None:
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

    def __init__(self, *, available_characters: Iterable[Character] = ()) -> None:
        ShowBase.__init__(self)
        self.fighters = []
        self.fsm = GameFSM(self)
        self.selected_characters = []
        self.index = 0
        self.world = None
        self.debugNP = None

        self.accept('main_menu', self.request, ['MainMenu'])
        self.accept(
            'character_menu',
            self.request,
            ['CharacterMenu', 'Select a Character', available_characters, 'view'],
        )
        self.accept(
            'fighter_selection',
            self.request,
            ['CharacterMenu', 'Select a Fighter', available_characters],
        )
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
                    self.fsm.character_menu.title_text[
                        'text'
                    ] = 'Select a Fighter, Player 2'
                else:
                    self.request('Battle', self.selected_characters)
            case 'copy':
                self.request('Battle', [character, character])

    def enter_battle(self, characters: Iterable[Character]) -> None:
        _logger.info(f'Starting battle with {characters}')
        # Set up the World
        self.world = physics.make_world(gravity=GRAVITY)
        self.cam.set_pos(0, -10, 2)
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

        for fighter in self.fighters:
            fighter.set_stance(stances.BOXING_STANCE)
        self.taskMgr.add(self.update, 'update')

    def update(self, task: Task) -> int:
        """Update the world using physics."""
        assert self.world is not None
        self.handle_collisions()
        return physics.update_physics(self.world, task)

    def handle_collisions(self) -> None:
        assert self.world is not None
        for manifold in self.world.manifolds:
            if not manifold.node0.into_collide_mask & manifold.node1.into_collide_mask:
                continue
            for node in (manifold.node0, manifold.node1):
                impact_callback = node.python_tags.get('impact_callback')
                if impact_callback is not None:
                    impact_callback(node, manifold)

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
        user.use_move(move, self.fighters[target_index])

    def next_turn(self) -> None:
        fighter = self.fighters[self.index]
        fighter.apply_current_effects()
        if fighter.hp <= 0:
            victor = self.fighters[1 - self.index]
            _logger.info(f'{victor} won the battle')
            messenger.send('announce_win', [victor.name])
        else:
            messenger.send('query_action', [self.index])


def main() -> None:
    """Run an instance of the app."""
    logger = logging.getLogger('joat')
    logger.setLevel(logging.DEBUG)
    file_handler = logging.FileHandler('log.log', mode='w')
    file_handler.setFormatter(
        logging.Formatter('[%(asctime)s] %(levelname)s - %(name)s - %(message)s')
    )
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
    stream_handler.setLevel(logging.WARNING)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    characters: list[Character] = []
    for fp in Path('data', 'characters').iterdir():
        with fp.open() as f:
            characters.append(Character.from_json(f))
    app = App(available_characters=characters)
    app.run()
