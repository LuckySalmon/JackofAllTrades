import math
import random

from direct.gui.DirectGui import *
from direct.showbase.DirectObject import DirectObject
from direct.showbase.ShowBase import ShowBase
from direct.showbase.ShowBaseGlobal import globalClock
from direct.task import Task
from panda3d.bullet import BulletDebugNode
from panda3d.bullet import BulletPlaneShape
from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletWorld
from panda3d.core import TextNode
from panda3d.core import Vec3, LQuaternion

import characters
import moves

frame_height = 0.5
frame_width = 0.5
button_height = 0.1
button_width = 0.25
window_height = 1
window_width = 4 / 3

gravity = 9.81


def create_quaternion(angle, axis):
    """Create a quaternion with the given characteristics"""
    radians = angle/360 * math.pi
    cosine = math.cos(radians/2)
    quaternion = LQuaternion(cosine, *axis)
    quaternion.normalize()
    return quaternion


class ShoulderMovingObject(DirectObject):
    def __init__(self, character_list):
        self.character_list = character_list
        bindings = [('q', 'e'), ('a', 'd'), ('z', 'c')]
        for axis, keys in enumerate(bindings):
            for i, key in enumerate(keys):
                self.accept(key, self.move_arms, [axis, (-1) ** i])
                self.accept(key + '-up', self.move_arms, [axis, 0])

    def move_arms(self, axis, speed):
        for i, character in enumerate(self.character_list):
            character.set_shoulder_motion(axis, (-1) ** (i+1) * speed)


class App(ShowBase):

    def __init__(self, character_list):
        ShowBase.__init__(self)

        self.clock = 0

        for character in character_list:
            character.HP = character.BaseHP
            # displayHP(Character)
        self.characterList = character_list
        self.buttons = []
        self.index = 0

        # Set up the World
        # The World
        self.world = BulletWorld()
        self.world.setGravity(Vec3(0, 0, -gravity))

        # Camera
        base.cam.setPos(0, -30, 4)
        base.cam.lookAt(0, 0, 2)

        # The Ground
        np = render.attachNewNode(BulletRigidBodyNode('Ground'))
        np.node().addShape(BulletPlaneShape(Vec3(0, 0, 1), 1))
        np.setPos(0, 0, -2)
        self.world.attachRigidBody(np.node())

        # Characters
        character_list[0].insert(self.world, render, -1, (-2, 0))
        character_list[1].insert(self.world, render, 1, (2, 0))

        # Debug
        debug_node = BulletDebugNode('Debug')
        debug_node.showWireframe(True)
        debug_node.showConstraints(True)
        debug_node.showBoundingBoxes(False)
        debug_node.showNormals(False)
        self.debugNP = render.attachNewNode(debug_node)
        self.debugNP.show()
        self.world.setDebugNode(self.debugNP.node())
        debug_object = DirectObject()
        debug_object.accept('f1', self.toggle_debug)

        # Testing Controls
        arms_down_object = DirectObject()
        arms_down_object.accept('arrow_down', self.arms_down)
        shoulder_moving_object = ShoulderMovingObject(character_list)

        self.taskMgr.add(self.update, 'update')

        # Set up GUI
        self.sharedInfo = OnscreenText(text="No information to display yet.",
                                       pos=(0, 0.5), scale=0.07,
                                       align=TextNode.ACenter, mayChange=1)
        self.actionBoxes, self.infoBoxes, self.useButtons, self.healthBars = [], [], [], []
        self.selectedAction, self.selection = None, None
        for side in (-1, 1):
            action_box = DirectFrame(frameColor=(0, 0, 0, 1),
                                     frameSize=(-frame_width, frame_width, -frame_height, frame_height),
                                     pos=(side * (window_width - frame_width), 0, -(window_height - frame_height)))
            info_box = OnscreenText(text="No info available", scale=0.07,
                                    align=TextNode.ACenter, mayChange=1)
            info_box.reparentTo(action_box)
            info_box.setPos(0, frame_height + 0.25)
            use_button = DirectButton(frameSize=(-button_width, button_width, -button_height, button_height),
                                      text="N/A", text_scale=0.1, borderWidth=(0.025, 0.025),
                                      command=self.use_action, state=DGG.DISABLED)
            use_button.reparentTo(action_box)
            use_button.setPos(frame_width - button_width, 0, 0)
            hp = self.characterList[0 if side < 0 else side].HP
            bar = DirectWaitBar(text="", range=hp, value=hp,
                                pos=(side * 0.5, 0, 0.75),
                                frameSize=(side * -0.4, side * 0.5, 0, -0.05))
            self.actionBoxes.append(action_box)
            self.infoBoxes.append(info_box)
            self.useButtons.append(use_button)
            self.healthBars.append(bar)

        self.query_action()

    def update(self, task):
        """Update the world using physics."""
        dt = globalClock.getDt()
        self.world.doPhysics(dt)
        self.clock += 1
        return Task.cont

    def arms_down(self):
        for character in self.characterList:
            character.arms_down()

    def toggle_debug(self):
        """Toggle debug display for physical objects."""
        if self.debugNP.isHidden():
            self.debugNP.show()
        else:
            self.debugNP.hide()

    def query_action(self):
        """Set up buttons for a player to choose an action."""
        character, frame = self.characterList[self.index], self.actionBoxes[self.index]
        for i, action in enumerate(character.moveList):
            b = DirectButton(frameSize=(-button_width, button_width, -button_height, button_height),
                             text=action, text_scale=0.1, borderWidth=(0.025, 0.025),
                             command=self.set_action, extraArgs=[character, action])
            b.reparentTo(frame)
            b.setPos(-(frame_width - button_width), 0, frame_height - (2 * i + 1) * button_height)
            self.buttons.append(b)

    def set_action(self, character, name):
        """Set an action to be selected."""
        i = self.index
        self.selectedAction = character.moveList[name]
        self.infoBoxes[i].setText(self.selectedAction.show_stats())
        self.useButtons[i].setText("Use %s" % name)
        self.useButtons[i]["state"] = DGG.NORMAL
        self.selection = name

    def use_action(self):
        """Make the character use the selected action, then move on to the next turn."""
        for button in self.useButtons:
            button["state"] = DGG.DISABLED
            button["text"] = "N/A"
        user = self.characterList[self.index]
        name, move = self.selection, self.selectedAction

        # Result of move
        if move.get_accuracy() > random.randint(0, 99):
            damage = move.get_damage()
            if random.randint(1, 100) <= 2:
                damage *= 1.5
                print("Critical Hit!".format(user.Name, name, damage))
            self.infoBoxes[self.index].setText("{}'s {} hit for {} damage!".format(user.Name, name, damage))
        else:
            damage = 0
            self.infoBoxes[self.index].setText("{}'s {} missed!".format(user.Name, name))

        # Move over to other character and apply damage
        self.index = (self.index + 1) % 2
        opponent = self.characterList[self.index]
        damage = min(max(damage - opponent.Defense, 0), opponent.HP)  # TODO: Find and use a better formula
        opponent.HP -= damage
        self.healthBars[self.index]["value"] -= damage
        self.infoBoxes[self.index].setText('{} took {} damage!'.format(opponent.Name, damage))

        # Reset GUI
        for button in self.buttons:
            button.destroy()
        self.buttons.clear()

        # Move on to next step (KO or opponent response)
        if opponent.HP <= 0:
            self.sharedInfo.setText('%s wins!' % user.Name)
            # I thought this would make the character fall, but it just glitches out
            self.characterList[self.index].torso.node().setMass(1.0)
            self.characterList[self.index].torso.node().setActive(True, False)
            for button in self.useButtons:
                button.destroy()
        else:
            self.query_action()
        # TODO: I would like to make this program focused entirely on graphics.
        #  I.e., other computations are handled externally and relevant results passed to functions from here.


def test():
    """Run a battle between two test characters for debug purposes."""
    attributes = dict(name='Test Jack', hp=10, speed=1, defense=1)
    char1 = characters.Character(attributes, char_moves=moves.defaultBasic)
    char2 = characters.Character(attributes, char_moves=moves.defaultBasic)
    app = App([char1, char2])
    app.run()
