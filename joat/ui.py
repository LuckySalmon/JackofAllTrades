from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Sequence
from itertools import product
from typing import Literal

from direct.gui.DirectGui import (
    DGG,
    DirectButton,
    DirectFrame,
    DirectWaitBar,
    OnscreenText,
)
from direct.showbase.DirectObject import DirectObject
from direct.showbase.MessengerGlobal import messenger
from panda3d.core import TextNode

from .characters import Character, Fighter
from .moves import Move

LEFT, RIGHT = -1, 1
ASPECT_RATIO = 4 / 3
SELECTOR_WIDTH = 0.5


def uniform_spacing(
    counts: Sequence[int], gaps: Sequence[float]
) -> Iterator[tuple[float, ...]]:
    """Yield tuples of coordinates such that there are `counts[i]`
    rows of points spaced `gaps[i]` apart along each axis `i`.
    """
    # Make a list of tuples representing the coordinates that points
    # should be generated at along each axis
    spots_by_axis = []
    for count, gap in zip(counts, gaps, strict=True):
        center = (count - 1) / 2
        spots = tuple((i - center) * gap for i in range(count))
        spots_by_axis.append(spots)
    # Yield a point for each combination of possible spots along each axis
    return product(*spots_by_axis)


class MainMenu:
    backdrop: DirectFrame
    battleButton: DirectButton
    characterButton: DirectButton
    quitButton: DirectButton

    def __init__(self) -> None:
        self.backdrop = DirectFrame(
            frameColor=(0, 0, 0, 0), frameSize=(-1, 1, -1, 1), pos=(0, 0, 0)
        )
        self.battleButton = self.make_button(
            'Go To Battle', ['fighter_selection', ['split_screen']], 0.4
        )
        self.characterButton = self.make_button(
            'Characters', ['character_menu'], 0
        )
        self.quitButton = self.make_button('Quit', ['quit'], -0.4)

    def make_button(
        self, text: str, event_args: Iterable, y: float
    ) -> DirectButton:
        return DirectButton(
            text=text,
            command=messenger.send,
            extraArgs=event_args,
            pos=(0, 0, y),
            frameSize=(-0.4, 0.4, -0.15, 0.15),
            borderWidth=(0.05, 0.05),
            text_scale=0.1,
            parent=self.backdrop,
        )

    def hide(self) -> None:
        self.backdrop.hide()

    def show(self) -> None:
        self.backdrop.show()


class CharacterMenu:
    mode: str
    selectedCharacter: Character | None
    backdrop: DirectFrame
    title_text: OnscreenText
    character_view: DirectFrame
    character_view_text: OnscreenText
    confirmation_button: DirectButton
    back_button: DirectButton
    buttons: list[DirectButton]

    def __init__(
        self,
        title: str,
        characters: Iterable[Character],
        mode: str,
    ) -> None:
        self.mode = mode
        self.selectedCharacter = None
        self.backdrop = DirectFrame(
            frameColor=(0, 0, 0, 0), frameSize=(-1, 1, -1, 1), pos=(0, 0, 0)
        )
        self.title_text = OnscreenText(
            text=title, pos=(0, 0.9), parent=self.backdrop
        )
        self.character_view = DirectFrame(
            frameColor=(0.2, 0.2, 0.2, 0.8),
            frameSize=(-ASPECT_RATIO, ASPECT_RATIO, -0.5, 0.5),
            pos=(0, 0, -0.5),
            parent=self.backdrop,
        )
        self.character_view_text = OnscreenText(
            text='Character customization is unimplemented',
            pos=(0, 0.2),
            parent=self.character_view,
        )
        self.confirmation_button = DirectButton(
            text='Select a Character',
            command=self.confirm_selection,
            pos=(0, 0, 0),
            frameSize=(-0.4, 0.4, -0.15, 0.15),
            borderWidth=(0.05, 0.05),
            text_scale=0.07,
            state=DGG.DISABLED,
            parent=self.character_view,
        )
        if mode == 'view':
            self.confirmation_button.hide()
        else:
            self.character_view_text.hide()
        self.character_view.hide()

        self.back_button = DirectButton(
            text='Back',
            command=lambda: messenger.send('main_menu'),
            pos=(-1.15, 0, 0.9),
            frameSize=(-2, 2, -1, 1),
            borderWidth=(0.2, 0.2),
            scale=0.05,
            parent=self.backdrop,
        )
        self.buttons = []
        for character, (x, y) in zip(
            characters, uniform_spacing((4, 4), (0.5, 0.5))
        ):
            button = DirectButton(
                text=character.name,
                command=self.select_character,
                extraArgs=[character],
                pos=(y, 0, -x - 0.2),
                frameSize=(-4, 4, -4, 4),
                borderWidth=(0.25, 0.25),
                scale=0.05,
                parent=self.backdrop,
            )
            self.buttons.append(button)

    def reset(self, characters: Iterable[Character], mode: str) -> None:
        self.selectedCharacter = None
        self.character_view.hide()
        self.mode = mode
        if mode == 'view':
            self.character_view_text.show()
            self.confirmation_button.hide()
        else:
            self.confirmation_button.show()
            self.character_view_text.hide()
        self.buttons.clear()
        button_positions = uniform_spacing((4, 4), (0.5, 0.5))
        for character, (x, y) in zip(characters, button_positions):
            button = DirectButton(
                text=character.name,
                command=self.select_character,
                extraArgs=[character],
                pos=(y, 0, -x - 0.2),
                frameSize=(-4, 4, -4, 4),
                borderWidth=(0.25, 0.25),
                scale=0.05,
                parent=self.backdrop,
            )
            self.buttons.append(button)

    def select_character(self, character: Character) -> None:
        self.character_view.show()
        self.selectedCharacter = character
        if self.mode != 'view':
            self.confirmation_button['text'] = f'Use {character.name}'
            self.confirmation_button['state'] = DGG.NORMAL

    def confirm_selection(self) -> None:
        messenger.send('select_character', [self.selectedCharacter, self.mode])

    def hide(self) -> None:
        self.backdrop.hide()

    def show(self) -> None:
        self.backdrop.show()


class BattleInterface(DirectObject):
    sharedInfo: OnscreenText
    actionSelectors: list[ActionSelector]
    infoBoxes: list[OnscreenText]
    healthBars: list[DirectWaitBar]

    def __init__(self, characters: Iterable[Fighter]) -> None:
        super().__init__()
        self.sharedInfo = OnscreenText(
            pos=(0, 0.5), scale=0.07, align=TextNode.ACenter
        )

        self.actionSelectors, self.infoBoxes, self.healthBars = [], [], []
        for character, side in zip(characters, (LEFT, RIGHT)):
            x = side * (ASPECT_RATIO - SELECTOR_WIDTH)
            index = 0 if side == LEFT else 1

            action_selector = ActionSelector(
                character.moves.values(), (x, 0, -0.5), index
            )
            action_selector.hide()

            info_box = OnscreenText(
                pos=(x, 0.25), scale=0.07, align=TextNode.ACenter
            )

            bar = DirectWaitBar(
                range=character.hp,
                value=character.hp,
                pos=(side * 0.5, 0, 0.75),
                frameSize=(side * -0.4, side * 0.5, 0, -0.05),
            )

            self.actionSelectors.append(action_selector)
            self.infoBoxes.append(info_box)
            self.healthBars.append(bar)

        self.accept('query_action', self.query_action)
        self.accept('remove_query', self.remove_query)
        self.accept('output_info', self.output_info)
        self.accept('set_health_bar', self.set_health_bar)
        self.accept('announce_win', self.announce_win)

    def query_action(self, index: int) -> None:
        """Set up buttons for a player to choose an action."""
        self.actionSelectors[index].show()

    def remove_query(self) -> None:
        for selector in self.actionSelectors:
            selector.hide()

    def output_info(self, index: int, info: str) -> None:
        self.infoBoxes[index].setText(info)

    def set_health_bar(self, index: int, health: int) -> None:
        self.healthBars[index]['value'] = health

    def announce_win(self, winner: str) -> None:
        self.sharedInfo.setText(f'{winner} wins!')


class ActionSelector:
    selected_action: Move | None
    index: int
    backdrop: DirectFrame
    use_buttons: list[DirectButton]
    action_buttons: list[DirectButton]

    def __init__(
        self,
        actions: Iterable[Move],
        pos: tuple[float, float, float],
        index: int,
    ) -> None:
        self.selected_action = None
        self.index = index

        self.backdrop = DirectFrame(
            frameColor=(0, 0, 0, 0.5),
            frameSize=(-SELECTOR_WIDTH, SELECTOR_WIDTH, -0.5, 0.5),
            pos=pos,
        )

        self.use_buttons = []
        for i, target in enumerate(('self', 'opponent')):
            y = (2 * i + 1) * 0.1
            button = self.make_button(
                f'Use on {target}',
                self.use_action,
                (SELECTOR_WIDTH / 2, 0, 0.5 - y),
                [target],
            )
            button.hide()
            self.use_buttons.append(button)

        self.action_buttons = []
        for i, action in enumerate(actions):
            y = (2 * i + 1) * 0.1
            button = self.make_button(
                action.name,
                self.select_action,
                (-SELECTOR_WIDTH / 2, 0, 0.5 - y),
                [action],
            )
            self.action_buttons.append(button)

    def make_button(
        self,
        text: str,
        command: Callable,
        pos: tuple[float, float, float],
        command_args: Iterable = (),
    ) -> DirectButton:
        return DirectButton(
            text=text,
            command=command,
            extraArgs=command_args,
            pos=pos,
            frameSize=(-SELECTOR_WIDTH / 2, SELECTOR_WIDTH / 2, -0.1, 0.1),
            borderWidth=(0.025, 0.025),
            text_scale=0.07,
            parent=self.backdrop,
        )

    def select_action(self, action: Move) -> None:
        self.selected_action = action
        messenger.send('output_info', [self.index, action.info()])
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

    def use_action(self, target: Literal['self', 'opponent']) -> None:
        target_index = self.index if target == 'self' else not self.index
        messenger.send('use_action', [self.selected_action, target_index])

    def hide(self) -> None:
        self.backdrop.hide()

    def show(self) -> None:
        self.backdrop.show()
