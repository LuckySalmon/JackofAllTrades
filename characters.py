import math
import winsound

from panda3d.bullet import BulletConeTwistConstraint, BulletGenericConstraint
from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletSphereShape, BulletBoxShape, BulletCapsuleShape
from panda3d.core import Vec3, TransformState, Point3, LMatrix3

enableSound = False
charList = ['regular', 'boxer', 'psycho', 'test']

identity = LMatrix3(1, 0, 0, 0, 1, 0, 0, 0, 1)


def arms(character):
    for suffix in ('_l', '_r'):
        bicep = getattr(character, 'bicep' + suffix)
        shoulder = getattr(character, 'shoulder' + suffix)
        yield bicep, shoulder  # This statement turns the whole function into a generator


def shoulder_angles(origin, point, theta, transform=identity):
    point -= origin
    point = transform.xform(point)

    l1, l2 = 1, 1
    q = point.normalized()
    dist = point.length()
    if dist > l1+l2:
        # cap the distance of the target to l1+l2
        dist = l1 + l2
        point = q * dist
    x, y, z = point

    # u1 and u2 form a basis for the plane perpendicular to OQ
    u1 = Vec3(z, 0, -x).normalized()
    u2 = Vec3(x*y, -x**2 - z**2, y*z).normalized()

    sp = (dist+l1+l2)/2                                     # semi-perimeter of OPQ
    r = (2/dist)*math.sqrt(sp*(sp-dist)*(sp-l1)*(sp-l2))    # distance from OQ to P
    d = (dist**2 + l1**2 - l2**2)/(2*dist)                  # length of projection of OP onto OQ
    elbow = u1*r*math.cos(theta) + u2*r*math.sin(theta) + q*d

    # e1, e2, and e3 describe a rotation matrix
    e1 = elbow.normalized()
    e2 = (point - e1*point.dot(e1)).normalized()
    e3 = e1.cross(e2)

    # alpha, beta, and gamma are the shoulder angles, while phi is the elbow angle
    alpha = math.atan2(e3[1], e1[1])
    beta = math.atan2(e2[1], e1[1]/math.cos(alpha))
    gamma = math.atan2(-e2[2]/math.cos(beta), -e2[0]/math.cos(beta))
    phi = math.acos((l1**2 + l2**2 - dist**2)/(2*l1*l2)) - math.pi
    return alpha, beta, gamma, phi


class Character(object):
    def __init__(self, attributes, xp=0, char_moves=()):
        self.Name = attributes['name'].title()
        self.BaseHP = int(attributes['hp'])
        self.HP = int(attributes['hp'])
        self.Speed = int(attributes['speed'])
        self.Defense = int(attributes['defense'])
        self.XP = xp
        self.Level = 1
        self.update_level()
        self.moveList = {}
        for move in char_moves:
            self.add_move(move)
        self.head = None
        self.torso = None
        self.bicep_l, self.bicep_r = None, None
        self.shoulder_l, self.shoulder_r = None, None
        self.shoulder_l_transform = LMatrix3(-1, 0, 0, 0, 1, 0, 0, 0, 1)
        self.shoulder_r_transform = LMatrix3(1, 0, 0, 0, -1, 0, 0, 0, -1)

    def insert(self, world, render, i, pos):
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

        x, y = pos

        # measurements below are in degrees
        neck_yaw_limit = 90
        neck_pitch_limit = 45
        shoulder_twist_limit = 90  # limit for twisting arm along the bicep axis
        shoulder_in_limit = 180  # maximum declination from T-pose towards torso
        shoulder_out_limit = 90  # maximum elevation from T-pose away from torso
        shoulder_forward_limit = 175  # maximum angle from down by side to pointing forward
        shoulder_backward_limit = 90  # maximum angle from down by side to pointing backward

        # Create a head
        head_node = BulletRigidBodyNode('Head')
        head_node.addShape(BulletSphereShape(head_radius))
        head_node.setMass(1.0)
        head_pointer = render.attachNewNode(head_node)
        head_pointer.setPos(x, y, head_elevation)
        world.attachRigidBody(head_node)

        # Create a torso
        torso_node = BulletRigidBodyNode('Torso')
        torso_node.addShape(BulletBoxShape(Vec3(torso_x, torso_y, torso_z)))
        torso_node.setMass(0.0)  # remain in place
        torso_pointer = render.attachNewNode(torso_node)
        torso_pointer.setPos(x, y, head_elevation - head_radius - torso_z)
        world.attachRigidBody(torso_node)

        # Create biceps
        bicep_l_node = BulletRigidBodyNode('BicepL')
        bicep_l_node.addShape(BulletCapsuleShape(bicep_radius, bicep_length, 1))
        bicep_l_node.setMass(0.25)
        bicep_l_pointer = render.attachNewNode(bicep_l_node)
        bicep_l_pointer.setPos(x, y - i*(torso_y + bicep_radius + shoulder_space + bicep_length / 2),
                               shoulder_elevation)
        world.attachRigidBody(bicep_l_node)

        bicep_r_node = BulletRigidBodyNode('BicepR')
        bicep_r_node.addShape(BulletCapsuleShape(bicep_radius, bicep_length, 1))
        bicep_r_node.setMass(0.25)
        bicep_r_pointer = render.attachNewNode(bicep_r_node)
        bicep_r_pointer.setPos(x, y + i*(torso_y + bicep_radius + shoulder_space + bicep_length / 2),
                               shoulder_elevation)
        world.attachRigidBody(bicep_r_node)

        # Attach the head to the torso
        head_frame = TransformState.makePosHpr(Point3(0, 0, -head_radius), Vec3(0, 0, -90))
        torso_frame = TransformState.makePosHpr(Point3(0, 0, torso_z), Vec3(0, 0, -90))
        neck = BulletConeTwistConstraint(head_node, torso_node, head_frame, torso_frame)
        neck.setDebugDrawSize(0.5)
        neck.setLimit(neck_pitch_limit, neck_pitch_limit, neck_yaw_limit)
        world.attachConstraint(neck)

        # Attach the biceps to the torso
        orientation = Vec3(0, 90, 0)

        torso_frame = TransformState.makePosHpr(Point3(0, (torso_y + shoulder_space + bicep_radius) * -i,
                                                       shoulder_elevation - torso_elevation), orientation)
        bicep_frame = TransformState.makePosHpr(Point3(0, i * bicep_length / 2, 0), orientation)
        shoulder_l = BulletGenericConstraint(torso_node, bicep_l_node, torso_frame, bicep_frame, True)

        torso_frame = TransformState.makePosHpr(Point3(0, (torso_y + shoulder_space + bicep_radius) * i,
                                                       shoulder_elevation - torso_elevation), orientation)
        bicep_frame = TransformState.makePosHpr(Point3(0, -i * bicep_length / 2, 0), orientation)
        shoulder_r = BulletGenericConstraint(torso_node, bicep_r_node, torso_frame, bicep_frame, True)

        shoulder_l.setAngularLimit(1, -shoulder_twist_limit, shoulder_twist_limit)
        shoulder_r.setAngularLimit(1, -shoulder_twist_limit, shoulder_twist_limit)
        if i < 0:
            shoulder_l.setAngularLimit(0, -shoulder_out_limit, shoulder_in_limit)
            shoulder_r.setAngularLimit(0, -shoulder_in_limit, shoulder_out_limit)
            shoulder_l.setAngularLimit(2, -shoulder_forward_limit, shoulder_backward_limit)
            shoulder_r.setAngularLimit(2, -shoulder_forward_limit, shoulder_backward_limit)
        else:
            shoulder_l.setAngularLimit(0, -shoulder_in_limit, shoulder_out_limit)
            shoulder_r.setAngularLimit(0, -shoulder_out_limit, shoulder_in_limit)
            shoulder_l.setAngularLimit(2, -shoulder_backward_limit, shoulder_forward_limit)
            shoulder_r.setAngularLimit(2, -shoulder_backward_limit, shoulder_forward_limit)

        shoulder_l.setDebugDrawSize(0.3)
        world.attachConstraint(shoulder_l, True)
        world.attachConstraint(shoulder_r, True)

        for shoulder in (shoulder_l, shoulder_r):
            for axis in range(3):
                shoulder.getRotationalLimitMotor(axis).setMaxMotorForce(200)

        self.head = head_pointer
        self.torso = torso_pointer
        self.bicep_l, self.bicep_r = bicep_l_pointer, bicep_r_pointer
        self.shoulder_l, self.shoulder_r = shoulder_l, shoulder_r
        self.shoulder_l_transform *= -i
        self.shoulder_r_transform *= -i

    def set_shoulder_motion(self, axis, speed):
        for i, (bicep, shoulder) in enumerate(arms(self)):
            motor = shoulder.getRotationalLimitMotor(axis)
            sign = (-1) ** i if axis < 2 else 1
            motor.setTargetVelocity(sign * speed)
            motor.setMotorEnabled(True)
            bicep.node().setActive(True, False)

    def position_shoulder(self, side, target):
        tol = 0.1
        speed = 1
        pos = Vec3(0, 0, 0)
        bicep = getattr(self, 'bicep_' + side)
        shoulder = getattr(self, 'shoulder_' + side)
        transform = getattr(self, 'shoulder_' + side + '_transform')
        target_angles = shoulder_angles(pos, target, 0, transform)
        for axis in range(3):
            motor = shoulder.getRotationalLimitMotor(axis)
            angle = shoulder.getAngle(axis)
            diff = target_angles[axis] - angle
            if abs(diff) > tol:
                motor.setTargetVelocity(speed * diff)
            else:
                motor.setTargetVelocity(0)
            motor.setMotorEnabled(True)
        bicep.node().setActive(True, False)

    def arms_down(self):
        for bicep, shoulder in arms(self):
            for i in range(3):
                shoulder.getRotationalLimitMotor(i).setMotorEnabled(False)
            bicep.node().setActive(True, False)

    def list_moves(self):  # isn't this redundant?
        """Check what moves this character has and return a list of available moves."""
        print(self.moveList)
        return self.moveList

    def add_move(self, move):
        """Attempt to add a move to this list of those available."""
        if len(self.moveList) < int(0.41 * self.Level + 4):
            # changed the above from <= as I'm assuming the formula is meant to be a cap, not one less than the cap
            self.moveList[move.name] = move
            if enableSound:
                winsound.Beep(600, 125)
                winsound.Beep(750, 100)
                winsound.Beep(900, 150)
        else:
            print("You have too many moves. Would you like to replace one?")
            if enableSound:
                winsound.Beep(600, 175)
                winsound.Beep(500, 100)

    def update_level(self):
        """Use a character's XP to increase their level."""
        while self.XP >= (threshold := self.Level * 1000):
            self.Level += 1
            self.XP -= threshold
        return self.Level

    # TODO: create various status affects


# def create_class(name, attributes, char_list):
#     """Insert a character into the list of those available."""
#     set_name = name + ' basic'
#     move_set = moves.sets[set_name] if set_name in moves.sets else moves.defaultBasic
#     char_list[name] = type(name, (Character,), {'__init__': lambda self: char_init(self,
#                                                                                    attributes, char_moves=move_set)})
#
#
# for class_name in attributeList:
#     create_class(class_name, attributeList[class_name], charList)
