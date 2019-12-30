from direct.gui.DirectGui import *
from direct.showbase.DirectObject import DirectObject
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.bullet import BulletDebugNode
from panda3d.bullet import BulletPlaneShape
from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletSphereShape
from panda3d.bullet import BulletSphericalConstraint
from panda3d.bullet import BulletWorld
from panda3d.core import TextNode
from panda3d.core import Vec3, Point3

import characters
import random

frame_height = 0.5
frame_width = 0.5
button_height = 0.1
button_width = 0.25
window_height = 1
window_width = 4 / 3


class App(ShowBase):

    def __init__(self, character_list):
        ShowBase.__init__(self)
        for character in character_list:
            character.HP = character.BaseHP
            # displayHP(Character)
        self.characterList = character_list
        self.buttons = []
        self.index = 0
        self.setUpWorld()
        self.characters = []
        self.constraints = []
        for i in (-1, 1):
            node_pointer, constraint = self.createCharacter(i)
            self.characters.append(node_pointer)
            self.constraints.append(constraint)
        self.taskMgr.add(self.update, 'update')
        self.setUpGUI()
        self.queryAction()

    def setUpWorld(self):
        # The World
        self.world = BulletWorld()
        self.world.setGravity(Vec3(0, 0, -9.81))

        # Camera
        base.cam.setPos(0, -30, 10)
        base.cam.lookAt(0, 0, 2)

        # The Ground
        np = render.attachNewNode(BulletRigidBodyNode('Ground'))
        np.node().addShape(BulletPlaneShape(Vec3(0, 0, 1), 1))
        np.setPos(0, 0, -2)
        self.world.attachRigidBody(np.node())

        # Debug
        debugNode = BulletDebugNode('Debug')
        debugNode.showWireframe(True)
        debugNode.showConstraints(True)
        debugNode.showBoundingBoxes(False)
        debugNode.showNormals(False)
        self.debugNP = render.attachNewNode(debugNode)
        self.debugNP.show()
        self.world.setDebugNode(self.debugNP.node())
        debugObject = DirectObject()
        debugObject.accept('f1', self.toggleDebug)

    def createCharacter(self, i):
        # An Orb as a character placeholder
        #   No mass means it cannot move
        node = BulletRigidBodyNode('Orb')
        node.addShape(BulletSphereShape(0.5))
        node.setMass(1.0)
        np = render.attachNewNode(node)
        np.setPos(i * 2, 0, 1.5)
        self.world.attachRigidBody(node)
        attach = BulletSphericalConstraint(node, Point3(0, 0, 0.25))
        self.world.attachConstraint(attach)
        return np, attach

    def update(self, task):
        dt = globalClock.getDt()
        self.world.doPhysics(dt)
        return Task.cont

    def toggleDebug(self):
        if self.debugNP.isHidden():
            self.debugNP.show()
        else:
            self.debugNP.hide()

    def setUpGUI(self):
        self.sharedInfo = OnscreenText(text="No information to display yet.",
                                       pos=(0, 0.5), scale=0.07,
                                       align=TextNode.ACenter, mayChange=1)
        self.actionBoxes, self.infoBoxes, self.useButtons, self.healthBars = [], [], [], []
        for side in (-1, 1):
            actionBox = DirectFrame(frameColor=(0, 0, 0, 1),
                                    frameSize=(-frame_width, frame_width, -frame_height, frame_height),
                                    pos=(side * (window_width - frame_width), 0, -(window_height - frame_height)))
            infoBox = OnscreenText(text="No info availible", scale=0.07,
                                   align=TextNode.ACenter, mayChange=1)
            infoBox.reparentTo(actionBox)
            infoBox.setPos(0, frame_height + 0.25)
            useButton = DirectButton(frameSize=(-button_width, button_width, -button_height, button_height),
                                     text="N/A", text_scale=0.1, borderWidth=(0.025, 0.025),
                                     command=self.useAction, state=DGG.DISABLED)
            useButton.reparentTo(actionBox)
            useButton.setPos(frame_width - button_width, 0, 0)
            HP = self.characterList[0 if side < 0 else side].HP
            bar = DirectWaitBar(text="", range=HP, value=HP,
                                pos=(side * 0.5, 0, 0.75),
                                frameSize=(side * -0.4, side * 0.5, 0, -0.05))
            self.actionBoxes.append(actionBox)
            self.infoBoxes.append(infoBox)
            self.useButtons.append(useButton)
            self.healthBars.append(bar)

    def queryAction(self):
        character, frame = self.characterList[self.index], self.actionBoxes[self.index]
        actions = character.moveList
        for i, action in enumerate(actions):
            b = DirectButton(frameSize=(-button_width, button_width, -button_height, button_height),
                             text=action, text_scale=0.1, borderWidth=(0.025, 0.025),
                             command=self.setAction, extraArgs=[character, action])
            b.reparentTo(frame)
            b.setPos(-(frame_width - button_width), 0, frame_height - (2 * i + 1) * button_height)
            self.buttons.append(b)

    def setAction(self, character, name):
        i = self.index
        self.selectedAction = character.moveList[name]
        self.infoBoxes[i].setText(self.selectedAction.showStats())
        self.useButtons[i].setText("Use %s" % name)
        self.useButtons[i]["state"] = DGG.NORMAL
        self.selection = name

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
        self.index = (self.index + 1) % 2
        opponent = self.characterList[self.index]
        damage = min(max(damage - opponent.Defense, 0), opponent.HP)  # is this how defense is supposed to work?
        opponent.HP -= damage
        self.healthBars[self.index]["value"] -= damage
        self.infoBoxes[self.index].setText('{} took {} damage!'.format(opponent.Name, damage))
        for button in self.buttons:
            button.destroy()
        self.buttons.clear()
        if opponent.HP <= 0:
            self.sharedInfo.setText('%s wins!' % user.Name)
            self.constraints[self.index].setEnabled(False)
            self.characters[self.index].node().setActive(True, False)
            for button in self.useButtons:
                button.destroy()
        else:
            self.queryAction()


def test():
    app = App([characters.charList['test'](), characters.charList['test']()])
    app.run()
