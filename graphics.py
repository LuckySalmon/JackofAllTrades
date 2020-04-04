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
from panda3d.bullet import BulletSphereShape, BulletBoxShape, BulletCapsuleShape
from panda3d.bullet import BulletSphericalConstraint, BulletConeTwistConstraint, BulletGenericConstraint
from panda3d.bullet import BulletRotationalLimitMotor
from panda3d.bullet import BulletWorld
from panda3d.core import TextNode
from panda3d.core import Vec3, Point3, TransformState, LQuaternion

import characters

frame_height = 0.5
frame_width = 0.5
button_height = 0.1
button_width = 0.25
window_height = 1
window_width = 4 / 3


def create_quaternion(angle, axis):
    """Create a quaternion with the given characteristics"""
    radians = angle/360 * math.pi
    cosine = math.cos(radians/2)
    quaternion = LQuaternion(cosine, *axis)
    quaternion.normalize()
    return quaternion


class App(ShowBase):

    def __init__(self, character_list):
        ShowBase.__init__(self)
        for character in character_list:
            character.HP = character.BaseHP
            # displayHP(Character)
        self.characterList = character_list
        self.buttons = []
        self.index = 0

        # Set up the World
        # The World
        self.world = BulletWorld()
        self.world.setGravity(Vec3(0, 0, -9.81))

        # Camera
        base.cam.setPos(0, -30, 4)
        base.cam.lookAt(0, 0, 2)

        # The Ground
        np = render.attachNewNode(BulletRigidBodyNode('Ground'))
        np.node().addShape(BulletPlaneShape(Vec3(0, 0, 1), 1))
        np.setPos(0, 0, -2)
        self.world.attachRigidBody(np.node())

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

        self.characters = [self.create_character(i) for i in (-1, 1)]
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

    def create_character(self, i):
        """Create a character skeleton and return a dictionary of pointers to its components"""
        # Important numbers
        head_radius = 0.5
        head_elevation = 1.5
        torso_x = 0.3
        torso_y = 0.5
        torso_z = 0.75
        bicep_radius = 0.15
        bicep_length = 0.75
        shoulder_space = 0.05

        shoulder_elevation = head_elevation - head_radius - 0.1 - bicep_radius
        torso_elevation = head_elevation - head_radius - torso_z

        # measurements below are in degrees
        neck_yaw_limit = 90
        neck_pitch_limit = 45
        shoulder_twist_limit = 0  # limit for twisting arm along the bicep axis
        shoulder_in_limit = 80  # maximum declination from T-pose towards torso
        shoulder_out_limit = 90  # maximum elevation from T-pose away from torso
        shoulder_forward_limit = 175  # maximum angle from down by side to pointing forward
        shoulder_backward_limit = 90  # maximum angle from down by side to pointing backward

        # Create a head
        head_node = BulletRigidBodyNode('Head')
        head_node.addShape(BulletSphereShape(head_radius))
        head_node.setMass(1.0)
        head_pointer = render.attachNewNode(head_node)
        head_pointer.setPos(i * 2, 0, head_elevation)
        self.world.attachRigidBody(head_node)

        # Create a torso
        torso_node = BulletRigidBodyNode('Torso')
        torso_node.addShape(BulletBoxShape(Vec3(torso_x, torso_y, torso_z)))
        torso_node.setMass(0.0)  # remain in place
        torso_pointer = render.attachNewNode(torso_node)
        torso_pointer.setPos(i * 2, 0, head_elevation - head_radius - torso_z)
        self.world.attachRigidBody(torso_node)

        # Create biceps
        bicep_l_node = BulletRigidBodyNode('BicepL')
        bicep_l_node.addShape(BulletCapsuleShape(bicep_radius, bicep_length, 1))
        bicep_l_node.setMass(0.25)
        bicep_l_pointer = render.attachNewNode(bicep_l_node)
        bicep_l_pointer.setPos(i * 2, -i*(torso_y + bicep_radius + shoulder_space + bicep_length/2), shoulder_elevation)
        self.world.attachRigidBody(bicep_l_node)

        bicep_r_node = BulletRigidBodyNode('BicepR')
        bicep_r_node.addShape(BulletCapsuleShape(bicep_radius, bicep_length, 1))
        bicep_r_node.setMass(0.25)
        bicep_r_pointer = render.attachNewNode(bicep_r_node)
        bicep_r_pointer.setPos(i * 2, i*(torso_y + bicep_radius + shoulder_space + bicep_length/2), shoulder_elevation)
        self.world.attachRigidBody(bicep_r_node)

        # Attach the head to the torso
        head_frame = TransformState.makePosHpr(Point3(0, 0, -head_radius), Vec3(0, 0, -90))
        torso_frame = TransformState.makePosHpr(Point3(0, 0, torso_z), Vec3(0, 0, -90))
        neck = BulletConeTwistConstraint(head_node, torso_node, head_frame, torso_frame)
        neck.setDebugDrawSize(0.5)
        neck.setLimit(neck_pitch_limit, neck_pitch_limit, neck_yaw_limit)
        self.world.attachConstraint(neck)

        # Attach the biceps to the torso
        torso_frame = TransformState.makePosHpr(Point3(0, (torso_y + shoulder_space + bicep_radius) * -i,
                                                       shoulder_elevation - torso_elevation), Vec3(90, 0, 0))
        bicep_frame = TransformState.makePosHpr(Point3(0, i*bicep_length/2, 0), Vec3(90, 0, 0))
        shoulder_l = BulletGenericConstraint(torso_node, bicep_l_node, torso_frame, bicep_frame, True)

        torso_frame = TransformState.makePosHpr(Point3(0, (torso_y + shoulder_space + bicep_radius) * i,
                                                       shoulder_elevation - torso_elevation), Vec3(90, 0, 0))
        bicep_frame = TransformState.makePosHpr(Point3(0, -i * bicep_length / 2, 0), Vec3(90, 0, 0))
        shoulder_r = BulletGenericConstraint(torso_node, bicep_r_node, torso_frame, bicep_frame, True)

        shoulder_l.setAngularLimit(0, -shoulder_twist_limit, shoulder_twist_limit)
        shoulder_r.setAngularLimit(0, -shoulder_twist_limit, shoulder_twist_limit)
        if i < 0:
            shoulder_l.setAngularLimit(1, -shoulder_in_limit, shoulder_out_limit)
            shoulder_r.setAngularLimit(1, -shoulder_out_limit, shoulder_in_limit)
            shoulder_l.setAngularLimit(2, -shoulder_backward_limit, shoulder_forward_limit)
            shoulder_r.setAngularLimit(2, -shoulder_backward_limit, shoulder_forward_limit)
        else:
            shoulder_l.setAngularLimit(1, -shoulder_out_limit, shoulder_in_limit)
            shoulder_r.setAngularLimit(1, -shoulder_in_limit, shoulder_out_limit)
            shoulder_l.setAngularLimit(2, -shoulder_forward_limit, shoulder_backward_limit)
            shoulder_r.setAngularLimit(2, -shoulder_forward_limit, shoulder_backward_limit)

        shoulder_l.setDebugDrawSize(0.3)
        self.world.attachConstraint(shoulder_l)
        self.world.attachConstraint(shoulder_r)

        # Move the arm to test things
        shoulder_motor = shoulder_l.getRotationalLimitMotor(2)
        shoulder_motor.setTargetVelocity(-5 * i)
        shoulder_motor.setMaxMotorForce(100)
        # shoulder_motor.setMotorEnabled(True)

        return dict(head=head_pointer, torso=torso_pointer, bicep_l=bicep_l_pointer, bicep_r=bicep_r_pointer)

    def update(self, task):
        """Update the world using physics."""
        dt = globalClock.getDt()
        self.world.doPhysics(dt)
        return Task.cont

    def toggle_debug(self):
        """Toggle debug display for physical objects."""
        if self.debugNP.isHidden():
            self.debugNP.show()
        else:
            self.debugNP.hide()

    def query_action(self):
        """Set up buttons for a player to choose an action."""
        character, frame = self.characterList[self.index], self.actionBoxes[self.index]
        for i, action in enumerate(actions := character.moveList):
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
        if success := (move.get_accuracy() > random.randint(0, 99)):
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
            self.characters[self.index]['torso'].node().setMass(1.0)
            self.characters[self.index]['torso'].node().setActive(True, False)
            for button in self.useButtons:
                button.destroy()
        else:
            self.query_action()
        # TODO: I would like to make this program focused entirely on graphics.
        #  I.e., other computations are handled externally and relevant results passed to functions from here.


def test():
    """Run a battle between two test characters for debug purposes."""
    app = App([characters.charList['test'](), characters.charList['test']()])
    app.run()
