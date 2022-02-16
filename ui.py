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

LEFT, RIGHT = -1, 1

frame_height = 0.5
frame_width = 0.5
button_height = 0.1
button_width = 0.25
window_height = 1
window_width = 4 / 3

default_button_args = dict(frameSize=(-button_width, button_width, -button_height, button_height),
                           borderWidth=(0.025, 0.025),
                           text_scale=0.1)


def even_spacing(dimensions, spacing):
    transforms = []
    for dim, space in zip(dimensions, spacing):
        shift = (dim - 1) / 2
        transforms.append(lambda i, d=shift, k=space: (i - d) * k)
    for index in product(*(range(d) for d in dimensions)):
        point = tuple(t(i) for i, t in zip(index, transforms))
        yield point


class MainMenu:
    def __init__(self):
        self.backdrop = DirectFrame(frameColor=(0, 0, 0, 0),
                                    frameSize=(-1, 1, -1, 1),
                                    pos=(0, 0, 0))
        self.battleButton = DirectButton(text='Go To Battle',
                                         command=messenger.send,
                                         extraArgs=['fighter_selection', ['split_screen']],
                                         pos=(0, 0, 0.4),
                                         frameSize=(-0.4, 0.4, -0.15, 0.15),
                                         borderWidth=(0.05, 0.05),
                                         text_scale=0.1,
                                         parent=self.backdrop)
        self.characterButton = DirectButton(text='Characters',
                                            command=lambda: messenger.send('character_menu'),
                                            pos=(0, 0, 0),
                                            frameSize=(-0.4, 0.4, -0.15, 0.15),
                                            borderWidth=(0.05, 0.05),
                                            text_scale=0.1,
                                            parent=self.backdrop)
        self.quitButton = DirectButton(text='Quit',
                                       command=lambda: messenger.send('quit'),
                                       pos=(0, 0, -0.4),
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
        for character, (x, y) in zip(characters, even_spacing((4, 4), (0.5, 0.5))):
            button = DirectButton(text=character.Name,
                                  command=self.select_character,
                                  extraArgs=[character],
                                  pos=(y, 0, -x),
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

        self.actionBoxes, self.infoBoxes, self.useButtons, self.healthBars = [], [], [], []
        for character, side in zip(character_list, (LEFT, RIGHT)):
            box_pos = (side * (window_width - frame_width), 0, frame_height - window_height)
            action_box = DirectFrame(frameColor=(0, 0, 0, 0.5),
                                     frameSize=(-frame_width, frame_width, -frame_height, frame_height),
                                     pos=box_pos)
            action_box.hide()

            info_box = OnscreenText(pos=(box_pos[0], box_pos[2] + frame_height + 0.25),
                                    scale=0.07,
                                    align=TextNode.ACenter)

            use_button = DirectButton(text='',
                                      command=lambda: messenger.send('use_action'),
                                      pos=(frame_width - button_width, 0, 0),
                                      parent=action_box,
                                      **default_button_args)

            bar = DirectWaitBar(range=character.HP,
                                value=character.HP,
                                pos=(side * 0.5, 0, 0.75),
                                frameSize=(side * -0.4, side * 0.5, 0, -0.05))

            count = len(character.moveList)
            heights = even_spacing((count,), (2 * button_height,))
            index = 0 if side < 0 else 1
            for action, (y,) in zip(character.moveList.values(), heights):
                DirectButton(text=action.name,
                             command=self.select_action,
                             extraArgs=[index, action],
                             pos=(button_width - frame_width, 0, frame_height - count * button_height - y),
                             parent=action_box,
                             **default_button_args)

            self.actionBoxes.append(action_box)
            self.infoBoxes.append(info_box)
            self.useButtons.append(use_button)
            self.healthBars.append(bar)

        self.accept('query_action', self.query_action)
        self.accept('remove_query', self.remove_query)
        self.accept('output_info', self.output_info)
        self.accept('apply_damage', self.apply_damage)
        self.accept('announce_win', self.announce_win)

    def query_action(self, index):
        """Set up buttons for a player to choose an action."""
        self.actionBoxes[index].show()

    def select_action(self, index, action):
        messenger.send('set_action', [action])
        self.output_info(index, action.show_stats())
        self.useButtons[index].setText(f'Use {action.name}')

    def remove_query(self):
        for box in self.actionBoxes:
            box.hide()

    def output_info(self, index, info):
        self.infoBoxes[index].setText(info)

    def apply_damage(self, index, damage, damaged):
        self.healthBars[index]['value'] -= damage
        self.output_info(index, f'{damaged} took {damage} damage!')

    def announce_win(self, winner):
        self.sharedInfo.setText(f'{winner} wins!')
