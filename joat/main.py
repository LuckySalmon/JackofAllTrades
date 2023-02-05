from __future__ import annotations

import functools
import logging
from collections.abc import Iterable
from pathlib import Path
from typing import Final

from direct.fsm.FSM import FSM
from direct.showbase.ShowBase import ShowBase
from panda3d.core import Vec3

from . import arenas, physics, stances, ui
from .characters import Character, Fighter

_logger: Final = logging.getLogger(__name__)

GRAVITY: Final = Vec3(0, 0, -9.81)


class GameFSM(FSM):
    app: App
    available_characters: list[Character]
    main_menu: ui.MainMenu | None = None
    character_menu: ui.CharacterMenu | None = None
    battle_interface: ui.BattleInterface | None = None

    def __init__(
        self, app: App, *, available_characters: Iterable[Character] = ()
    ) -> None:
        FSM.__init__(self, 'GameFSM')
        self.app = app
        self.available_characters = list(available_characters)
        self.request('MainMenu')

    def enterMainMenu(self) -> None:
        if self.main_menu is not None:
            self.main_menu.show()
        else:
            self.main_menu = ui.MainMenu(
                battle_function=functools.partial(
                    self.request, 'CharacterMenu', 'Select a Fighter', 'split_screen'
                ),
                character_function=functools.partial(
                    self.request, 'CharacterMenu', 'Select a Character', 'view'
                ),
                quit_function=self.app.userExit,
            )

    def exitMainMenu(self) -> None:
        if self.main_menu is not None:
            self.main_menu.hide()

    def enterCharacterMenu(self, title: str, mode: str) -> None:
        if mode == 'split_screen':
            title += ', Player 1'
        if self.character_menu is not None:
            self.character_menu.reset(mode)
            self.character_menu.show()
        else:
            self.character_menu = ui.CharacterMenu(
                title=title,
                characters=self.available_characters,
                mode=mode,
                character_select_function=self.app.select_character,
            )

    def exitCharacterMenu(self) -> None:
        if self.character_menu is not None:
            self.character_menu.hide()

    def enterBattle(self, characters: Iterable[Character]) -> None:
        self.app.enter_battle(characters)
        assert self.app.arena is not None
        self.battle_interface = ui.BattleInterface(self.app.arena)
        self.battle_interface.query_action(0)


class App(ShowBase):
    fsm: GameFSM
    selected_characters: list[Character]
    index: int = 0
    arena: arenas.Arena | None = None

    def __init__(self, *, available_characters: Iterable[Character] = ()) -> None:
        ShowBase.__init__(self)
        self.fsm = GameFSM(self, available_characters=available_characters)
        self.selected_characters = []
        self.accept('main_menu', self.fsm.request, ['MainMenu'])
        self.accept(
            'next_turn',
            lambda: self.taskMgr.add(self.next_turn, delay=1, extraArgs=()),
        )

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
                    self.fsm.request('Battle', self.selected_characters)
            case 'copy':
                self.fsm.request('Battle', [character, character])

    def enter_battle(self, characters: Iterable[Character]) -> None:
        characters = sorted(characters, key=lambda c: c.speed)
        _logger.info(f'Starting battle with {characters}')
        world = physics.make_world(gravity=GRAVITY)
        self.cam.set_pos(0, -10, 2)
        self.cam.look_at(0, 0, 0)
        fighters: list[Fighter] = []
        for i, character in enumerate(characters):
            fighter = Fighter.from_character(character, world, i)
            fighter.set_stance(stances.BOXING_STANCE)
            fighters.append(fighter)
        self.arena = arenas.Arena(*fighters, world=world)
        self.taskMgr.add(self.arena.update, 'update')

    def next_turn(self) -> None:
        assert self.arena is not None
        assert self.fsm.battle_interface is not None
        self.index = (self.index + 1) % 2
        fighter = self.arena.get_fighter(self.index)
        fighter.apply_current_effects()
        if fighter.hp <= 0:
            victor = self.arena.get_fighter(1 - self.index)
            _logger.info(f'{victor} won the battle')
            self.fsm.battle_interface.announce_win(victor.name)
        else:
            self.fsm.battle_interface.query_action(self.index)


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
