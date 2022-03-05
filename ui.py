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
from collections.abc import Generator, Sequence

LEFT, RIGHT = -1, 1

frame_height = 0.5
frame_width = 0.5
button_height = 0.1
button_width = 0.25
window_height = 1
window_width = 4 / 3


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

    def make_button(self, text, event_args, y):
        return DirectButton(text=text,
                            command=messenger.send,
                            extraArgs=event_args,
                            pos=(0, 0, y),
                            frameSize=(-0.4, 0.4, -0.15, 0.15),
                            borderWidth=(0.05, 0.05),
                            text_scale=0.1,
                            parent=self.backdrop)

    def hide(self):
        self.backdrop.hide()


class CharacterMenu:
    def __init__(self, title, characters, mode):
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
                                          frameSize=(-window_width, window_width, -window_height/2, window_height/2),
                                          pos=(0, 0, -window_height/2),
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

    def select_character(self, character):
        self.character_view.show()
        self.selectedCharacter = character
        if self.mode != 'view':
            self.confirmation_button['text'] = f'Use {character.Name}'
            self.confirmation_button['state'] = DGG.NORMAL

    def confirm_selection(self):
        messenger.send('select_character', [self.selectedCharacter, self.mode])

    def hide(self):
        self.backdrop.hide()


class BattleInterface(DirectObject):
    def __init__(self, character_list):
        super().__init__()
        self.sharedInfo = OnscreenText(pos=(0, 0.5), scale=0.07, align=TextNode.ACenter)

        self.actionSelectors, self.infoBoxes, self.healthBars = [], [], []
        for character, side in zip(character_list, (LEFT, RIGHT)):
            pos = (side * (window_width - frame_width), 0, frame_height - window_height)
            index = 0 if side == LEFT else 1

            action_selector = ActionSelector(character.moveList.values(), pos, index)
            action_selector.hide()

            info_box = OnscreenText(pos=(pos[0], pos[2] + frame_height + 0.25),
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

    def query_action(self, index):
        """Set up buttons for a player to choose an action."""
        self.actionSelectors[index].show()

    def remove_query(self):
        for selector in self.actionSelectors:
            selector.hide()

    def output_info(self, index, info):
        self.infoBoxes[index].setText(info)

    def apply_damage(self, index, damage, damaged):
        self.healthBars[index]['value'] -= damage
        self.output_info(index, f'{damaged} took {damage} damage!')

    def announce_win(self, winner):
        self.sharedInfo.setText(f'{winner} wins!')


class ActionSelector:
    def __init__(self, actions, pos, index):
        self.selected_action = None
        self.index = index

        self.backdrop = DirectFrame(frameColor=(0, 0, 0, 0.5),
                                    frameSize=(-frame_width, frame_width, -frame_height, frame_height),
                                    pos=pos)

        self.use_button = self.make_button('', self.use_action, (button_width, 0, 0))
        self.use_button.hide()

        self.action_buttons = []
        for i, action in enumerate(actions):
            y = (2*i + 1) * button_height
            button = self.make_button(action.name, self.select_action, (-button_width, 0, frame_height - y), [action])
            self.action_buttons.append(button)

    def make_button(self, text, command, pos, command_args=()):
        return DirectButton(text=text,
                            command=command,
                            extraArgs=command_args,
                            pos=pos,
                            frameSize=(-button_width, button_width, -button_height, button_height),
                            borderWidth=(0.025, 0.025),
                            text_scale=0.07,
                            parent=self.backdrop)

    def select_action(self, action):
        self.selected_action = action
        messenger.send('output_info', [self.index, action.show_stats()])
        self.use_button.setText(f'Use {action.name}')
        self.use_button.show()

    def use_action(self):
        messenger.send('use_action', [self.selected_action])

    def hide(self):
        self.backdrop.hide()

    def show(self):
        self.backdrop.show()
