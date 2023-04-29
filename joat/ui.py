from __future__ import annotations

import collections
import itertools
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from typing_extensions import Self

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


@dataclass
class MainMenu:
    backdrop: DirectFrame = field(default_factory=DirectFrame)
    buttons: Sequence[DirectButton] = ()

    @classmethod
    def construct(cls, *tuples: tuple[str, Callable[[], object]]) -> Self:
        backdrop = DirectFrame()
        center = (len(tuples) + 1) / 2
        buttons: list[DirectButton] = []
        for i, (name, callback) in enumerate(tuples, start=1):
            button = DirectButton(
                text=name,
                command=callback,
                pos=(0, 0, (center - i) * 0.4),
                frameSize=(-0.4, 0.4, -0.15, 0.15),
                borderWidth=(0.05, 0.05),
                text_scale=0.1,
                parent=backdrop,
            )
            buttons.append(button)
        return cls(backdrop, buttons)

    def hide(self) -> None:
        self.backdrop.hide()

    def show(self) -> None:
        self.backdrop.show()


class CharacterMenu:
    selection: Character | None = None
    backdrop: DirectFrame
    character_view: DirectFrame
    confirmation_button: DirectButton | None = None

    def __init__(
        self,
        characters: Iterable[Character],
        *,
        confirmation_callback: Callable[[Character], object] | None = None,
        back_callback: Callable[[], object] | None = None,
        aspect_ratio: float = 4 / 3,
    ) -> None:
        self.backdrop = DirectFrame(frameColor=(0, 0, 0, 0), frameSize=(-1, 1, -1, 1))
        OnscreenText(text='Select a Character', pos=(0, 0.9), parent=self.backdrop)
        self.character_view = DirectFrame(
            frameColor=(0.2, 0.2, 0.2, 0.8),
            frameSize=(-aspect_ratio, aspect_ratio, -0.5, 0.5),
            pos=(0, 0, -0.5),
            parent=self.backdrop,
        )
        if confirmation_callback is None:
            OnscreenText(
                text='Character customization is unimplemented',
                pos=(0, 0.2),
                parent=self.character_view,
            )
        else:
            self.confirmation_button = DirectButton(
                text='',
                command=confirmation_callback,
                frameSize=(-0.4, 0.4, -0.15, 0.15),
                borderWidth=(0.05, 0.05),
                text_scale=0.07,
                parent=self.character_view,
            )
        self.character_view.hide()
        DirectButton(
            text='Back',
            command=back_callback,
            pos=(-1.15, 0, 0.9),
            frameSize=(-2, 2, -1, 1),
            borderWidth=(0.2, 0.2),
            scale=0.05,
            parent=self.backdrop,
        )
        for char, (x, y) in zip(characters, uniform_spacing((4, 4), (0.5, 0.5))):
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

    def reset(self) -> None:
        self.selection = None
        self.character_view.hide()

    def select_character(self, character: Character) -> None:
        self.character_view.show()
        if self.confirmation_button is not None:
            self.confirmation_button['text'] = f'Use {character.name}'
            self.confirmation_button['extraArgs'] = [character]

    def hide(self) -> None:
        self.backdrop.hide()
        self.reset()

    def show(self) -> None:
        self.backdrop.show()


@dataclass
class InfoStream:
    backdrop: NodePath
    lines: collections.deque[OnscreenText] = field(default_factory=collections.deque)
    max_lines: int = field(default=16, kw_only=True)
    height: float = field(default=1.9, kw_only=True)

    @classmethod
    def make_default(cls) -> Self:
        return cls(
            DirectFrame(
                pos=(4 / 3 - 0.5, 0, 0),
                frameSize=(-0.5, 0.5, -1, 1),
                frameColor=(0, 0, 0, 0.25),
            )
        )

    def append_text(self, *new_lines: str) -> None:
        for new_line in new_lines:
            self.lines.appendleft(OnscreenText(new_line, parent=self.backdrop))
            if len(self.lines) > self.max_lines:
                old_line = self.lines.pop()
                old_line.destroy()
        line_spacing = 1 / (self.max_lines - 1)
        for i, line in enumerate(self.lines):
            line.set_pos(0, 0, self.height * (i * line_spacing - 0.5))

    def destroy(self) -> None:
        for line in self.lines:
            line.destroy()
        self.lines.clear()
        self.backdrop.remove_node()


@dataclass
class BattleMenu:
    interfaces: Iterable[FighterInterface]
    info_stream: InfoStream = field(default_factory=InfoStream.make_default)
    acceptor: DirectObject = field(default_factory=DirectObject, kw_only=True)

    @classmethod
    def from_fighters(cls, *fighters: Fighter) -> Self:
        interfaces: list[FighterInterface] = []
        for fighter in fighters:
            interface = FighterInterface(
                fighter.moves.values(),
                pos=(0.5 - 4 / 3, 0, -0.5),
                width=0.5,
                hidden=True,
            )
            interfaces.append(interface)
        return cls(interfaces)

    def __post_init__(self) -> None:
        self.acceptor.accept('output_info', self.output_info)

    def output_info(self, info: str) -> None:
        self.info_stream.append_text(info)

    def destroy(self) -> None:
        self.acceptor.ignore_all()
        self.info_stream.destroy()
        for interface in self.interfaces:
            interface.destroy()


class FighterInterface:
    selected_target: moves.Target | None = None
    selected_action: moves.Move | None = None
    backdrop: DirectFrame
    use_buttons: dict[moves.Target, DirectButton]
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
        self.use_buttons = {}
        for i, target in enumerate(moves.Target):
            button = DirectButton(
                text=f'Use on {target.value}',
                command=self.select_target,
                extraArgs=[target],
                pos=(width / 2, 0, 0.4 - 0.2 * i),
                **button_kwargs,
            )
            button.hide()
            self.use_buttons[target] = button
        self.action_buttons = []
        for i, action in enumerate(available_moves):
            button = DirectButton(
                text=action.name,
                command=self.select_action,
                extraArgs=[action],
                pos=(-width / 2, 0, 0.4 - i * 0.2),
                **button_kwargs,
            )
            self.action_buttons.append(button)
        if hidden:
            self.hide()

    def select_action(self, action: moves.Move) -> None:
        self.selected_action = action
        self.info_box.setText(f'{action.name}\n{action.accuracy}%')
        for target, button in self.use_buttons.items():
            if target in action.valid_targets:
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

    def destroy(self) -> None:
        for button in self.action_buttons:
            button.destroy()
        for button in self.use_buttons.values():
            button.destroy()
