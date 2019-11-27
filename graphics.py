from direct.showbase.ShowBase import ShowBase
from panda3d.core import TextNode
from direct.gui.OnscreenText import OnscreenText
from direct.gui.DirectGui import *

import moves, characters, random

frame_height = 0.5
frame_width = 0.5
button_height = 0.1
button_width = 0.25
window_height = 1
window_width = 4/3

class App(ShowBase):

    def __init__(self, characterList):
        ShowBase.__init__(self)
        self.sharedInfo = OnscreenText(text="No information to display yet.",
                                       pos=(0, 0.5), scale=0.07,
                                       align=TextNode.ACenter, mayChange=1)
        for character in characterList:
            character.HP = character.BaseHP
            #displayHP(Character)
        self.actionBoxes, self.infoBoxes, self.useButtons, self.healthBars = [], [], [], []
        for side in (-1, 1):
            actionBox = DirectFrame(frameColor=(0, 0, 0, 1),
                                    frameSize=(-frame_width, frame_width, -frame_height, frame_height),
                                    pos=(side*(window_width-frame_width), 0, -(window_height-frame_height)))
            infoBox = OnscreenText(text="No info availible", scale=0.07,
                                   align=TextNode.ACenter, mayChange=1)
            infoBox.reparentTo(actionBox)
            infoBox.setPos(0, frame_height+0.25)
            useButton = DirectButton(frameSize=(-button_width, button_width, -button_height, button_height),
                                     text="N/A", text_scale=0.1, borderWidth=(0.025, 0.025),
                                     command=self.useAction, state = DGG.DISABLED)
            useButton.reparentTo(actionBox)
            useButton.setPos(frame_width-button_width, 0, 0)
            i = 0 if side<0 else side
            HP = characterList[0 if side<0 else side].HP
            bar = DirectWaitBar(text="", range=HP, value=HP,
                             pos=(side*0.5, 0, 0.75),
                             frameSize=(side*-0.4, side*0.5, 0, -0.05))
            self.actionBoxes.append(actionBox)
            self.infoBoxes.append(infoBox)
            self.useButtons.append(useButton)
            self.healthBars.append(bar)
        self.buttons = []
        self.characterList = characterList
        self.index = 0
        self.chooseAction()

    def chooseAction(self):
        i = self.index
        character = self.characterList[i]
        actionBox = self.actionBoxes[i]
        self.createButtons(character, actionBox)

    def useAction(self):
        for button in self.useButtons:
            button["state"] = DGG.DISABLED
            button["text"] = "N/A"
        user = self.characterList[self.index]
        name, move = self.selection, self.selectedAction
        success = move.getAccuracy() > random.randint(0, 99)
        if success:
            damage = move.getDamage()
            if random.randint(1, 100) <= 2:
                damage *= 1.5
                print("Critical Hit!".format(user.Name, name, damage))
            self.infoBoxes[self.index].setText("{}'s {} hit for {} damage!".format(user.Name, name, damage))
        else:
            damage = 0
            self.infoBoxes[self.index].setText("{}'s {} missed!".format(user.Name, name))
        self.index = (self.index+1) % 2
        opponent = self.characterList[self.index]
        damage = min(max(damage - opponent.Defense, 0), opponent.HP)   #is this how defense is supposed to work?
        opponent.HP -= damage
        self.healthBars[self.index]["value"] -= damage
        self.infoBoxes[self.index].setText('{} took {} damage!'.format(opponent.Name, damage))
        for button in self.buttons:
            button.destroy()
        self.buttons.clear()
        if opponent.HP <= 0:
            self.sharedInfo.setText('%s wins!'%(user.Name))
            for button in self.useButtons:
                button.destroy()
        else:
            self.chooseAction()

    def setAction(self, character, name):
        i = self.index
        self.selectedAction = character.moveList[name]
        self.infoBoxes[i].setText(self.selectedAction.showStats())
        self.useButtons[i].setText("Use %s"%name)
        self.useButtons[i]["state"] = DGG.NORMAL
        self.selection = name

    def createButtons(self, character, frame):
        actions = character.moveList
        for i, action in enumerate(actions):
            b = DirectButton(frameSize=(-button_width, button_width, -button_height, button_height),
                             text=action, text_scale=0.1, borderWidth=(0.025, 0.025),
                             command=self.setAction, extraArgs=[character, action])
            b.reparentTo(frame)
            b.setPos(-(frame_width-button_width), 0, frame_height-(2*i+1)*button_height)
            self.buttons.append(b)

def test():
    app = App([characters.charList['test'](), characters.charList['test']()])  
    app.run()
