from direct.gui.DirectGui import *
from panda3d.core import TextNode


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


class BattleInterface:
    def __init__(self, character_list, use_action):
        self.buttons = []
        self.sharedInfo = OnscreenText(pos=(0, 0.5), scale=0.07, align=TextNode.ACenter)
        self.characterList = character_list

        self.actionBoxes, self.infoBoxes, self.useButtons, self.healthBars = [], [], [], []
        for side in (LEFT, RIGHT):
            action_box = DirectFrame(frameColor=(0, 0, 0, 1),
                                     frameSize=(-frame_width, frame_width, -frame_height, frame_height),
                                     pos=(side * (window_width - frame_width), 0, -(window_height - frame_height)))

            info_box = OnscreenText(pos=(0, frame_height + 0.25),
                                    scale=0.07,
                                    align=TextNode.ACenter,
                                    parent=action_box)

            use_button = DirectButton(text='',
                                      command=use_action,
                                      pos=(frame_width - button_width, 0, 0),
                                      state=DGG.DISABLED,
                                      parent=action_box,
                                      **default_button_args)

            hp = character_list[0 if side > 0 else 1].HP
            bar = DirectWaitBar(range=hp, value=hp,
                                pos=(side * 0.5, 0, 0.75),
                                frameSize=(side * -0.4, side * 0.5, 0, -0.05))

            self.actionBoxes.append(action_box)
            self.infoBoxes.append(info_box)
            self.useButtons.append(use_button)
            self.healthBars.append(bar)

    def query_action(self, character, index, command):
        """Set up buttons for a player to choose an action."""
        for i, action in enumerate(character.moveList):
            button = DirectButton(text=action,
                                  command=command,
                                  extraArgs=[character, action],
                                  pos=(-(frame_width - button_width), 0, frame_height - (2 * i + 1) * button_height),
                                  parent=self.actionBoxes[index],
                                  **default_button_args)
            self.buttons.append(button)

    def select_action(self, index, name):
        self.useButtons[index].setText(f'Use {name}')
        self.useButtons[index]['state'] = DGG.NORMAL

    def remove_query(self):
        for button in self.useButtons:
            button['state'] = DGG.DISABLED
            button['text'] = 'N/A'

        for button in self.buttons:
            button.destroy()
        self.buttons.clear()

    def output_info(self, index, info):
        self.infoBoxes[index].setText(info)

    def apply_damage(self, index, damage, damaged):
        self.healthBars[index]['value'] -= damage
        self.output_info(index, f'{damaged} took {damage} damage!')

    def announce_win(self, winner):
        self.sharedInfo.setText(f'{winner} wins!')
        for button in self.useButtons:
            button.destroy()


