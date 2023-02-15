from __future__ import annotations

import functools
import logging
import math
from collections.abc import Iterable
from pathlib import Path
from typing import Final

from direct.showbase.ShowBase import ShowBase
from panda3d.core import PythonTask, Vec3

from . import arenas, physics, stances, ui
from .characters import Character, Fighter

_logger: Final = logging.getLogger(__name__)

GRAVITY: Final = Vec3(0, 0, -9.81)


class App(ShowBase):
    available_characters: list[Character]
    selected_characters: list[Character]
    index: int = 0
    arena: arenas.Arena | None = None
    battle_menu: ui.BattleMenu | None = None
    character_menu: ui.CharacterMenu
    main_menu: ui.MainMenu

    def __init__(self, *, available_characters: Iterable[Character] = ()) -> None:
        ShowBase.__init__(self)
        self.available_characters = list(available_characters)
        self.selected_characters = []
        self.accept('main_menu', self.enter_main_menu)
        self.accept(
            'next_turn',
            lambda: self.taskMgr.add(self.next_turn, delay=1, extraArgs=()),
        )
        self.main_menu = ui.MainMenu(
            battle_function=functools.partial(
                self.enter_character_menu, 'split_screen'
            ),
            character_function=functools.partial(self.enter_character_menu, 'view'),
            quit_function=self.userExit,
        )
        self.character_menu = ui.CharacterMenu(
            characters=self.available_characters,
            character_select_function=self.select_character,
        )
        self.enter_main_menu()

    def enter_main_menu(self) -> None:
        self.character_menu.hide()
        self.main_menu.show()

    def enter_character_menu(self, mode: str = 'view') -> None:
        self.main_menu.hide()
        self.character_menu.reset(mode)
        self.character_menu.show()

    def select_character(self, character: Character, mode: str) -> None:
        match mode:
            case 'split_screen':
                self.selected_characters.append(character)
                if len(self.selected_characters) > 1:
                    self.enter_battle(*self.selected_characters)
            case 'copy':
                self.enter_battle(character, character)

    def enter_battle(self, character_1: Character, character_2: Character) -> None:
        self.main_menu.hide()
        self.character_menu.hide()
        if character_2.speed > character_1.speed:
            character_1, character_2 = character_2, character_1
        _logger.info(f'Starting battle with {character_1} and {character_2}')
        self.set_camera_pos(r=10, theta=1.2 * math.pi, height=2)
        world = physics.make_world(gravity=GRAVITY)
        fighter_1 = Fighter.from_character(character_1, world, 0)
        fighter_2 = Fighter.from_character(character_2, world, 1)
        fighter_1.set_stance(stances.BOXING_STANCE)
        fighter_2.set_stance(stances.BOXING_STANCE)
        self.arena = arenas.Arena(fighter_1, fighter_2, world=world)
        self.taskMgr.add(self.arena.update, 'update')
        self.battle_menu = ui.BattleMenu(self.arena)
        self.battle_menu.query_action(0)

    def set_camera_pos(self, *, r: float, theta: float, height: float) -> None:
        self.cam.set_pos(r * math.cos(theta), r * math.sin(theta), height)
        self.cam.look_at(0, 0, 0)

    def move_camera(self, to_angle: float, *, time: float = 1) -> PythonTask:
        x, y, height = self.cam.get_pos()
        from_angle = math.atan2(y, x)
        r = math.hypot(x, y)
        speed = (to_angle - from_angle) / time

        def update_camera_pos(task: PythonTask) -> int:
            if task.time < time:
                current_angle = from_angle + speed * task.time
                self.set_camera_pos(r=r, theta=current_angle, height=height)
                return PythonTask.DS_cont
            else:
                self.set_camera_pos(r=r, theta=to_angle, height=height)
                return PythonTask.DS_done

        return self.taskMgr.add(update_camera_pos)

    def next_turn(self) -> None:
        assert self.arena is not None
        assert self.battle_menu is not None
        self.index = (self.index + 1) % 2
        fighter = self.arena.get_fighter(self.index)
        fighter.apply_current_effects()
        if fighter.hp <= 0:
            victor = self.arena.get_fighter(1 - self.index)
            _logger.info(f'{victor} won the battle')
            self.battle_menu.output_info(f'{victor.name} wins!')
        else:
            self.move_camera((0.2 if self.index else 1.2) * math.pi)
            self.battle_menu.query_action(self.index)


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
