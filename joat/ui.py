from __future__ import annotations

import collections
import itertools
from collections.abc import Callable, Iterable, Iterator, Sequence
from typing_extensions import Self

import attrs
import imgui
from attrs import field
from direct.gui.DirectGui import DirectButton, DirectFrame, OnscreenText
from direct.showbase.DirectObject import DirectObject
from panda3d.core import AsyncTaskPause

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


@attrs.define
class MainMenu:
    backdrop: DirectFrame = attrs.Factory(DirectFrame)
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


@attrs.define
class InfoStream:
    lines: collections.deque[str] = attrs.Factory(collections.deque)

    @classmethod
    def make_default(cls) -> Self:
        lines = collections.deque(('' for _ in range(16)), maxlen=16)
        return cls(lines)

    def append_text(self, *new_lines: str) -> None:
        self.lines.extendleft(new_lines)

    def draw(self) -> None:
        for line in reversed(self.lines):
            imgui.text(line)


@attrs.define
class BattleMenu:
    interfaces: Iterable[FighterInterface]
    info_stream: InfoStream = field(factory=InfoStream.make_default)
    acceptor: DirectObject = field(factory=DirectObject, kw_only=True)

    @classmethod
    def from_fighters(cls, *fighters: Fighter) -> Self:
        return cls([FighterInterface.for_fighter(fighter) for fighter in fighters])

    def __attrs_post_init__(self) -> None:
        self.acceptor.accept('output_info', self.output_info)

    def draw(self) -> None:
        for i, interface in enumerate(self.interfaces):
            if interface.shown:
                imgui.set_next_window_position(60, 60, imgui.FIRST_USE_EVER)
                imgui.set_next_window_size(180, 180, imgui.FIRST_USE_EVER)
                with imgui.begin(f'Select a move:##{i}'):
                    interface.draw()
        imgui.set_next_window_position(500, 60, imgui.FIRST_USE_EVER)
        imgui.set_next_window_size(250, 310, imgui.FIRST_USE_EVER)
        with imgui.begin('Info'):
            self.info_stream.draw()

    def output_info(self, info: str) -> None:
        self.info_stream.append_text(info)

    def destroy(self) -> None:
        self.acceptor.ignore_all()


@attrs.define(kw_only=True)
class FighterInterface:
    available_moves: Iterable[moves.Move]
    text: str = ''
    selected_target: moves.Target | None = field(default=None, init=False)
    selected_action: moves.Move | None = field(default=None, init=False)
    shown: bool = field(default=False, init=False)

    @classmethod
    def for_fighter(cls, fighter: Fighter) -> Self:
        return cls(available_moves=fighter.moves.values())

    def draw(self) -> None:
        imgui.text(self.text)
        with imgui.begin_group():
            for action in self.available_moves:
                if imgui.button(action.name):
                    self.selected_action = action
                    self.text = f'{action.name}\nAccuracy: {action.accuracy}%'
        imgui.same_line()
        if self.selected_action is None:
            imgui.text('Select a move...')
            return
        with imgui.begin_group():
            for target in moves.Target:
                if target in self.selected_action.valid_targets:
                    if imgui.button(f'Use on {target.value}'):
                        self.selected_target = target

    async def query_action(self) -> tuple[moves.Move, moves.Target]:
        self.show()
        while self.selected_target is None or self.selected_action is None:
            await AsyncTaskPause(0)
        assert self.selected_target is not None
        assert self.selected_action is not None
        action, target = self.selected_action, self.selected_target
        self.selected_target = None
        return action, target

    def hide(self) -> None:
        self.shown = False

    def show(self) -> None:
        self.shown = True
