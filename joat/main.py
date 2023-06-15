from __future__ import annotations

import itertools
import json
import logging
import math
from collections.abc import Iterable
from pathlib import Path
from typing import Final, Protocol

import imgui
from direct.showbase.ShowBase import ShowBase
from panda3d.core import AsyncTaskPause, ClockObject, GraphicsWindow, Vec3

from . import arenas, moves, physics, spatial, stances, tasks, ui
from .characters import Action, Character, Fighter
from .panda_imgui import Panda3DRenderer

_logger: Final = logging.getLogger(__name__)

GRAVITY: Final = Vec3(0, 0, -9.81)


class SupportsDraw(Protocol):
    def draw(self) -> object:
        ...


class App:
    base: ShowBase
    available_characters: list[Character]
    selected_characters: list[Character]
    character_menu: ui.CharacterMenu
    fighter_menu: ui.CharacterMenu
    main_menu: ui.MainMenu
    drawing: bool = True

    def __init__(
        self,
        *,
        available_characters: Iterable[Character] = (),
        base: ShowBase | None = None,
    ) -> None:
        self.base = base or ShowBase()
        self.available_characters = list(available_characters)
        self.selected_characters = []
        self.main_menu = ui.MainMenu.construct(
            ('Go To Battle', self.enter_fighter_menu),
            ('Characters', self.enter_character_menu),
            ('Quit', self.base.userExit),
        )
        self.character_menu = ui.CharacterMenu(
            characters=self.available_characters,
            back_callback=self.enter_main_menu,
        )
        self.fighter_menu = ui.CharacterMenu(
            characters=self.available_characters,
            confirmation_callback=self.select_character,
            back_callback=self.enter_main_menu,
        )
        self.enter_main_menu()

    def run(self) -> None:
        self.base.run()

    def enter_main_menu(self) -> None:
        self.character_menu.hide()
        self.fighter_menu.hide()
        self.main_menu.show()

    def enter_character_menu(self) -> None:
        self.main_menu.hide()
        self.fighter_menu.hide()
        self.character_menu.show()

    def enter_fighter_menu(self) -> None:
        self.main_menu.hide()
        self.character_menu.hide()
        self.fighter_menu.show()

    def select_character(self, character: Character) -> None:
        self.selected_characters.append(character)
        if len(self.selected_characters) > 1:
            self.enter_battle(*self.selected_characters)
            self.selected_characters.clear()

    def enter_battle(self, character_1: Character, character_2: Character) -> None:
        self.main_menu.hide()
        self.character_menu.hide()
        self.fighter_menu.hide()
        if character_2.speed > character_1.speed:
            character_1, character_2 = character_2, character_1
        _logger.info(f'Starting battle with {character_1} and {character_2}')
        self.set_camera_pos(r=10, theta=1.2 * math.pi, height=3)
        root = self.base.render.attach_new_node('Arena Root')
        world = physics.make_world(gravity=GRAVITY)
        arena = arenas.Arena(root, world)

        fighter_1 = character_1.make_fighter(
            xform=spatial.make_rigid_transform(translation=Vec3(-0.5, 0, 0))
        )
        fighter_2 = character_2.make_fighter(
            xform=spatial.make_rigid_transform(
                rotation=spatial.make_rotation(math.pi, Vec3.unit_z()),
                translation=Vec3(0.5, 0, 0),
            )
        )
        if fighter_1.name == fighter_2.name:
            fighter_1.name += ' (1)'
            fighter_2.name += ' (2)'
        fighter_1.set_stance(stances.BOXING_STANCE)
        fighter_2.set_stance(stances.BOXING_STANCE)

        tasks.add_task(arena.update())
        tasks.add_task(self.do_battle(arena, fighter_1, fighter_2))

    def set_camera_pos(self, *, r: float, theta: float, height: float) -> None:
        self.base.cam.set_pos(r * math.cos(theta), r * math.sin(theta), height)
        self.base.cam.look_at(0, 0, 0)

    async def move_camera(self, to_angle: float, *, time: float = 1) -> None:
        clock = ClockObject.get_global_clock()
        start_time = clock.frame_time
        x, y, height = self.base.cam.get_pos()
        from_angle = math.atan2(y, x)
        r = math.hypot(x, y)
        speed = (to_angle - from_angle) / time
        while (dt := clock.frame_time - start_time) < time:
            current_angle = from_angle + speed * dt
            self.set_camera_pos(r=r, theta=current_angle, height=height)
            await AsyncTaskPause(0)
        self.set_camera_pos(r=r, theta=to_angle, height=height)

    async def draw(self, menu: SupportsDraw) -> None:
        assert isinstance(self.base.win, GraphicsWindow)
        imgui.create_context()
        renderer = Panda3DRenderer(self.base.win)
        while self.drawing:
            imgui.new_frame()
            menu.draw()
            imgui.render()
            renderer.render(imgui.get_draw_data())
            await AsyncTaskPause(0)

    async def do_battle(
        self, arena: arenas.Arena, fighter_1: Fighter, fighter_2: Fighter
    ) -> None:
        fighter_1.enter_arena(arena)
        fighter_2.enter_arena(arena)
        self.drawing = True
        battle_menu = ui.BattleMenu.from_fighters(fighter_1, fighter_2)
        tasks.add_task(self.draw(battle_menu))
        fighters = (fighter_1, fighter_2)
        interfaces = tuple(battle_menu.interfaces)
        for i in itertools.cycle(range(2)):
            interface = interfaces[i]
            fighter = fighters[i]
            opponent = fighters[1 - i]
            move, target = await interface.query_action()
            interface.hide()
            if target is moves.Target.SELF:
                await fighter.use_move(move, fighter)
            elif target is moves.Target.OTHER:
                await fighter.use_move(move, opponent)
            opponent.apply_current_effects()
            if opponent.health <= 0:
                _logger.info(f'{fighter} won the battle')
                battle_menu.output_info(f'{fighter.name} wins!')
                break
            else:
                await AsyncTaskPause(0.5)
                await self.move_camera((1.2 if i else 0.2) * math.pi)
        await AsyncTaskPause(5)
        self.drawing = False
        battle_menu.destroy()
        fighter_1.exit_arena()
        fighter_2.exit_arena()
        arena.exit()
        self.enter_main_menu()


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
    move_dict: dict[str, Action] = {}
    characters: list[Character] = []
    for fp in Path('data', 'moves').iterdir():
        j = json.loads(fp.read_text())
        move = moves.make_move_from_json(j)
        move_dict[fp.stem] = move
    for fp in Path('data', 'characters').iterdir():
        j = json.loads(fp.read_text())
        character = Character.from_json(j, move_dict=move_dict)
        characters.append(character)
    app = App(available_characters=characters)
    app.run()
