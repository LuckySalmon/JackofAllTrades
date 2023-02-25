from __future__ import annotations

import collections
import itertools
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field

from direct.gui.DirectGui import DirectButton, DirectFrame, OnscreenText
from direct.showbase.DirectObject import DirectObject
from panda3d.core import AsyncTaskPause, NodePath, TextNode

from . import moves
from .characters import Character, Fighter


def uniform_spacing(
    counts: Iterable[int], gaps: Iterable[float]
) -> Iterator[tuple[float, ...]]:
    """Yield tuples of coordinates such that there are `counts[i]`
    rows of points spaced `gaps[i]` apart along each axis `i`.
    """
    # Make a list of tuples representing the coordinates that points
    # should be generated at along each axis
    spots_by_axis: list[list[float]] = []
    for count, gap in zip(counts, gaps, strict=True):
        center = (count - 1) / 2
        spots = [(i - center) * gap for i in range(count)]
        spots_by_axis.append(spots)
    # Yield a point for each combination of possible spots along each axis
    return itertools.product(*spots_by_axis)


class MainMenu:
    backdrop: DirectFrame
    battle_button: DirectButton
    character_button: DirectButton
    quit_button: DirectButton

    def __init__(
        self,
        *,
        battle_function: Callable[[], object],
        character_function: Callable[[], object],
        quit_function: Callable[[], object],
    ) -> None:
        self.backdrop = DirectFrame(frameColor=(0, 0, 0, 0), frameSize=(-1, 1, -1, 1))
        construction_kwargs = {
            'frameSize': (-0.4, 0.4, -0.15, 0.15),
            'borderWidth': (0.05, 0.05),
            'text_scale': 0.1,
            'parent': self.backdrop,
        }
        self.battle_button = DirectButton(
            text='Go To Battle',
            command=battle_function,
            pos=(0, 0, 0.4),
            **construction_kwargs,
        )
        self.character_button = DirectButton(
            text='Characters',
            command=character_function,
            pos=(0, 0, 0),
            **construction_kwargs,
        )
        self.quit_button = DirectButton(
            text='Quit',
            command=quit_function,
            pos=(0, 0, -0.4),
            **construction_kwargs,
        )

    def hide(self) -> None:
        self.backdrop.hide()

    def show(self) -> None:
        self.backdrop.show()


class CharacterMenu:
    mode: str
    selection: Character | None = None
    backdrop: DirectFrame
    title_text: OnscreenText
    character_view: DirectFrame
    character_view_text: OnscreenText
    confirmation_button: DirectButton
    back_button: DirectButton
    buttons: list[DirectButton]

    def __init__(
        self,
        characters: Iterable[Character],
        mode: str = 'view',
        *,
        character_select_function: Callable[[Character, str], object],
        main_menu_function: Callable[[], object],
        aspect_ratio: float = 4 / 3,
    ) -> None:
        self.mode = mode
        self.backdrop = DirectFrame(frameColor=(0, 0, 0, 0), frameSize=(-1, 1, -1, 1))
        self.title_text = OnscreenText(
            text='Select a Character', pos=(0, 0.9), parent=self.backdrop
        )
        self.character_view = DirectFrame(
            frameColor=(0.2, 0.2, 0.2, 0.8),
            frameSize=(-aspect_ratio, aspect_ratio, -0.5, 0.5),
            pos=(0, 0, -0.5),
            parent=self.backdrop,
        )
        self.character_view_text = OnscreenText(
            text='Character customization is unimplemented',
            pos=(0, 0.2),
            parent=self.character_view,
        )

        def confirm_selection():
            assert self.selection is not None
            character_select_function(self.selection, self.mode)

        self.confirmation_button = DirectButton(
            text='',
            command=confirm_selection,
            frameSize=(-0.4, 0.4, -0.15, 0.15),
            borderWidth=(0.05, 0.05),
            text_scale=0.07,
            parent=self.character_view,
        )
        if mode == 'view':
            self.confirmation_button.hide()
        else:
            self.character_view_text.hide()
        self.character_view.hide()

        self.back_button = DirectButton(
            text='Back',
            command=main_menu_function,
            pos=(-1.15, 0, 0.9),
            frameSize=(-2, 2, -1, 1),
            borderWidth=(0.2, 0.2),
            scale=0.05,
            parent=self.backdrop,
        )
        self.buttons = [
            DirectButton(
                text=char.name,
                command=self.select_character,
                extraArgs=[char],
                pos=(y, 0, -x - 0.2),
                frameSize=(-4, 4, -4, 4),
                borderWidth=(0.25, 0.25),
                scale=0.05,
                parent=self.backdrop,
            )
            for char, (x, y) in zip(characters, uniform_spacing((4, 4), (0.5, 0.5)))
        ]

    def reset(self, mode: str) -> None:
        self.selection = None
        self.character_view.hide()
        self.mode = mode
        if mode == 'view':
            self.character_view_text.show()
            self.confirmation_button.hide()
        else:
            self.confirmation_button.show()
            self.character_view_text.hide()

    def select_character(self, character: Character) -> None:
        self.character_view.show()
        self.selection = character
        if self.mode != 'view':
            self.confirmation_button['text'] = f'Use {character.name}'

    def hide(self) -> None:
        self.backdrop.hide()

    def show(self) -> None:
        self.backdrop.show()


@dataclass
class InfoStream:
    backdrop: NodePath
    lines: collections.deque[OnscreenText] = field(default_factory=collections.deque)
    max_lines: int = field(default=16, kw_only=True)
    height: float = field(default=1.9, kw_only=True)

    def append_text(self, *new_lines: str) -> None:
        for new_line in new_lines:
            self.lines.appendleft(OnscreenText(new_line, parent=self.backdrop))
            if len(self.lines) > self.max_lines:
                old_line = self.lines.pop()
                old_line.destroy()
        line_spacing = 1 / (self.max_lines - 1)
        for i, line in enumerate(self.lines):
            line.set_pos(0, 0, self.height * (i * line_spacing - 0.5))


class BattleMenu(DirectObject):
    info_stream: InfoStream
    interfaces: list[FighterInterface]

    def __init__(
        self,
        *fighters: Fighter,
        aspect_ratio: float = 4 / 3,
        selector_width: float = 0.5,
    ) -> None:
        super().__init__()
        self.info_stream = InfoStream(
            DirectFrame(
                pos=(aspect_ratio - 0.5, 0, 0),
                frameSize=(-0.5, 0.5, -1, 1),
                frameColor=(0, 0, 0, 0.25),
            )
        )
        self.interfaces = [
            FighterInterface(
                fighter.moves.values(),
                pos=(selector_width - aspect_ratio, 0, -0.5),
                width=selector_width,
                hidden=True,
            )
            for fighter in fighters
        ]
        self.accept('output_info', self.output_info)

    def output_info(self, info: str) -> None:
        self.info_stream.append_text(info)


class FighterInterface:
    selected_target: moves.Target | None = None
    selected_action: moves.Move | None = None
    backdrop: DirectFrame
    use_buttons: list[DirectButton]
    action_buttons: list[DirectButton]
    info_box: OnscreenText

    def __init__(
        self,
        available_moves: Iterable[moves.Move],
        *,
        pos: tuple[float, float, float],
        width: float = 0.5,
        hidden: bool = False,
    ) -> None:
        self.backdrop = DirectFrame(
            frameColor=(0, 0, 0, 0.5),
            frameSize=(-width, width, -0.5, 0.5),
            pos=pos,
        )
        self.info_box = OnscreenText(
            parent=self.backdrop,
            pos=(0, 0.75),
            scale=0.07,
            align=TextNode.ACenter,
        )
        button_kwargs = {
            'frameSize': (-width / 2, width / 2, -0.1, 0.1),
            'borderWidth': (0.025, 0.025),
            'text_scale': 0.07,
            'parent': self.backdrop,
        }
        self.use_buttons = [
            DirectButton(
                text='Use on self',
                command=self.select_target,
                extraArgs=[moves.Target.SELF],
                pos=(width / 2, 0, 0.4),
                **button_kwargs,
            ),
            DirectButton(
                text='Use on opponent',
                command=self.select_target,
                extraArgs=[moves.Target.OTHER],
                pos=(width / 2, 0, 0.2),
                **button_kwargs,
            ),
        ]
        for button in self.use_buttons:
            button.hide()
        self.action_buttons = [
            DirectButton(
                text=action.name,
                command=self.select_action,
                extraArgs=[action],
                pos=(-width / 2, 0, 0.4 - i * 0.2),
                **button_kwargs,
            )
            for i, action in enumerate(available_moves)
        ]
        if hidden:
            self.hide()

    def select_action(self, action: moves.Move) -> None:
        self.selected_action = action
        self.info_box.setText(f'{action.name}\n{action.accuracy}%')
        button_visibility: tuple[bool, bool]
        if action.target == 'self':
            button_visibility = (True, False)
        elif action.target == 'other':
            button_visibility = (False, True)
        else:
            button_visibility = (True, True)
        for visible, button in zip(button_visibility, self.use_buttons):
            if visible:
                button.show()
            else:
                button.hide()

    def select_target(self, target: moves.Target) -> None:
        self.selected_target = target

    async def query_action(self) -> tuple[moves.Move, moves.Target]:
        self.show()
        while self.selected_target is None or self.selected_action is None:
            await AsyncTaskPause(0)
        assert self.selected_target is not None
        assert self.selected_action is not None
        action, target = self.selected_action, self.selected_target
        self.hide()
        del self.selected_target
        return action, target

    def hide(self) -> None:
        self.backdrop.hide()

    def show(self) -> None:
        self.backdrop.show()
