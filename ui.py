from direct.gui.DirectGui import (
    DGG,
    DirectButton,
    DirectFrame,
    DirectWaitBar,
    OnscreenText,
)
from direct.showbase.MessengerGlobal import messenger
from direct.showbase.DirectObject import DirectObject
from panda3d.core import TextNode
from itertools import product
from collections.abc import Callable, Generator, Iterable, Sequence

from characters import Character, Fighter
from moves import Move

LEFT, RIGHT = -1, 1
ASPECT_RATIO = 4 / 3
SELECTOR_WIDTH = 0.5


def uniform_spacing(counts: Sequence[int], gaps: Sequence[float]) -> Generator[tuple[float, ...]]:
    assert len(counts) == len(gaps)
    lists = []
    for count, gap in zip(counts, gaps):
        center = (count - 1) / 2
        L = [(i - center) * gap for i in range(count)]
        lists.append(L)
    index_ranges = [range(n) for n in counts]
    for index in product(*index_ranges):
        yield tuple(L[i] for i, L in zip(index, lists))


class MainMenu:
    def __init__(self):
        self.backdrop = DirectFrame(frameColor=(0, 0, 0, 0),
                                    frameSize=(-1, 1, -1, 1),
                                    pos=(0, 0, 0))
        self.battleButton = self.make_button('Go To Battle', ['fighter_selection', ['split_screen']], 0.4)
        self.characterButton = self.make_button('Characters', ['character_menu'], 0)
        self.quitButton = self.make_button('Quit', ['quit'], -0.4)

    def make_button(self, text: str, event_args: Iterable, y: float) -> DirectButton:
        return DirectButton(text=text,
                            command=messenger.send,
                            extraArgs=event_args,
                            pos=(0, 0, y),
                            frameSize=(-0.4, 0.4, -0.15, 0.15),
                            borderWidth=(0.05, 0.05),
                            text_scale=0.1,
                            parent=self.backdrop)

    def hide(self) -> None:
        self.backdrop.hide()


class CharacterMenu:
    def __init__(self, title: str, characters: Iterable[Character], mode: str):
        self.mode = mode
        self.selectedCharacter = None
        self.character_view = None
        self.backdrop = DirectFrame(frameColor=(0, 0, 0, 0),
                                    frameSize=(-1, 1, -1, 1),
                                    pos=(0, 0, 0))
        self.title_text = OnscreenText(text=title,
                                       pos=(0, 0.9),
                                       parent=self.backdrop)
        self.character_view = DirectFrame(frameColor=(.2, .2, .2, .8),
                                          frameSize=(-ASPECT_RATIO, ASPECT_RATIO, -0.5, 0.5),
                                          pos=(0, 0, -0.5),
                                          parent=self.backdrop)
        self.character_view_text = OnscreenText(text='Character customization is unimplemented',
                                                pos=(0, 0.2),
                                                parent=self.character_view)
        self.confirmation_button = DirectButton(text='Select a Character',
                                                command=self.confirm_selection,
                                                pos=(0, 0, 0),
                                                frameSize=(-.4, .4, -.15, .15),
                                                borderWidth=(.05, .05),
                                                text_scale=.07,
                                                state=DGG.DISABLED,
                                                parent=self.character_view)
        if mode == 'view':
            self.confirmation_button.hide()
        else:
            self.character_view_text.hide()
        self.character_view.hide()

        self.back_button = DirectButton(text='Back',
                                        command=lambda: messenger.send('main_menu'),
                                        pos=(-1.15, 0, 0.9),
                                        frameSize=(-2, 2, -1, 1),
                                        borderWidth=(.2, .2),
                                        scale=0.05,
                                        parent=self.backdrop)
        self.buttons = []
        for character, (x, y) in zip(characters, uniform_spacing((4, 4), (0.5, 0.5))):
            button = DirectButton(text=character.Name,
                                  command=self.select_character,
                                  extraArgs=[character],
                                  pos=(y, 0, -x - 0.2),
                                  frameSize=(-4, 4, -4, 4),
                                  borderWidth=(0.25, 0.25),
                                  scale=0.05,
                                  parent=self.backdrop)
            self.buttons.append(button)

    def select_character(self, character: Character) -> None:
        self.character_view.show()
        self.selectedCharacter = character
        if self.mode != 'view':
            self.confirmation_button['text'] = f'Use {character.Name}'
            self.confirmation_button['state'] = DGG.NORMAL

    def confirm_selection(self) -> None:
        messenger.send('select_character', [self.selectedCharacter, self.mode])

    def hide(self) -> None:
        self.backdrop.hide()


class BattleInterface(DirectObject):
    def __init__(self, character_list: list[Fighter]):
        super().__init__()
        self.sharedInfo = OnscreenText(pos=(0, 0.5), scale=0.07, align=TextNode.ACenter)

        self.actionSelectors, self.infoBoxes, self.healthBars = [], [], []
        for character, side in zip(character_list, (LEFT, RIGHT)):
            x = side * (ASPECT_RATIO - SELECTOR_WIDTH)
            index = 0 if side == LEFT else 1

            action_selector = ActionSelector(character.moveList.values(), (x, 0, -0.5), index)
            action_selector.hide()

            info_box = OnscreenText(pos=(x, 0.25),
                                    scale=0.07,
                                    align=TextNode.ACenter)

            bar = DirectWaitBar(range=character.HP,
                                value=character.HP,
                                pos=(side * 0.5, 0, 0.75),
                                frameSize=(side * -0.4, side * 0.5, 0, -0.05))

            self.actionSelectors.append(action_selector)
            self.infoBoxes.append(info_box)
            self.healthBars.append(bar)

        self.accept('query_action', self.query_action)
        self.accept('remove_query', self.remove_query)
        self.accept('output_info', self.output_info)
        self.accept('apply_damage', self.apply_damage)
        self.accept('announce_win', self.announce_win)

    def query_action(self, index: int) -> None:
        """Set up buttons for a player to choose an action."""
        self.actionSelectors[index].show()

    def remove_query(self) -> None:
        for selector in self.actionSelectors:
            selector.hide()

    def output_info(self, index: int, info: str) -> None:
        self.infoBoxes[index].setText(info)

    def apply_damage(self, index: int, damage: float, damaged: str) -> None:
        self.healthBars[index]['value'] -= damage
        self.output_info(index, f'{damaged} took {damage} damage!')

    def announce_win(self, winner: str) -> None:
        self.sharedInfo.setText(f'{winner} wins!')


class ActionSelector:
    def __init__(self, actions: Iterable[Move], pos: tuple[float, float, float], index: int):
        self.selected_action = None
        self.index = index

        self.backdrop = DirectFrame(frameColor=(0, 0, 0, 0.5),
                                    frameSize=(-SELECTOR_WIDTH, SELECTOR_WIDTH, -0.5, 0.5),
                                    pos=pos)

        self.use_button = self.make_button('', self.use_action, (SELECTOR_WIDTH/2, 0, 0))
        self.use_button.hide()

        self.action_buttons = []
        for i, action in enumerate(actions):
            y = (2*i + 1) * 0.1
            button = self.make_button(action.name, self.select_action, (-SELECTOR_WIDTH/2, 0, 0.5 - y), [action])
            self.action_buttons.append(button)

    def make_button(self,
                    text: str,
                    command: Callable,
                    pos: tuple[float, float, float],
                    command_args: Iterable = ()) -> DirectButton:
        return DirectButton(text=text,
                            command=command,
                            extraArgs=command_args,
                            pos=pos,
                            frameSize=(-SELECTOR_WIDTH/2, SELECTOR_WIDTH/2, -0.1, 0.1),
                            borderWidth=(0.025, 0.025),
                            text_scale=0.07,
                            parent=self.backdrop)

    def select_action(self, action: Move) -> None:
        self.selected_action = action
        messenger.send('output_info', [self.index, action.show_stats()])
        self.use_button.setText(f'Use {action.name}')
        self.use_button.show()

    def use_action(self) -> None:
        messenger.send('use_action', [self.selected_action])

    def hide(self) -> None:
        self.backdrop.hide()

    def show(self) -> None:
        self.backdrop.show()
