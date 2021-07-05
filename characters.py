import math
import winsound
import json
import moves

from panda3d.bullet import BulletConeTwistConstraint, BulletGenericConstraint, BulletHingeConstraint
from panda3d.bullet import BulletRigidBodyNode
from panda3d.bullet import BulletSphereShape, BulletBoxShape, BulletCapsuleShape
from panda3d.core import Vec3, VBase4, TransformState, Point3, LMatrix3, LMatrix4
from direct.directtools.DirectGeometry import LineNodePath

enableSound = False
charList = ['regular', 'boxer', 'psycho', 'test']
LEFT, RIGHT = -1, 1
shape_constructors = dict(sphere=BulletSphereShape,
                          box=lambda *args: BulletBoxShape(Vec3(*args)),
                          capsule_x=lambda *args: BulletCapsuleShape(*args, 0),
                          capsule_y=lambda *args: BulletCapsuleShape(*args, 1),
                          capsule_z=lambda *args: BulletCapsuleShape(*args, 2))


def draw_lines(lines: LineNodePath, *paths: dict, origin=None, relative=True):
    if origin is None:
        origin = lines.getCurrentPosition()
    lines.reset()
    for path in paths:
        if 'color' in path:
            lines.setColor(*path['color'])
        points = path['points']
        lines.moveTo(*origin)
        for point in points:
            if relative:
                point += origin
            lines.drawTo(*point)
    lines.create()


def make_rigid_transform(rotation, translation):
    """Return a TransformState comprising the given rotation followed by the given translation"""
    return TransformState.makeMat(LMatrix4(rotation, translation))


def make_body(name, shape, dimensions, mass, position, parent, world):
    constructor = shape_constructors[shape]
    node = BulletRigidBodyNode(name)
    shape = constructor(*dimensions)
    node.addShape(shape)
    node.setMass(mass)
    pointer = parent.attachNewNode(node)
    pointer.setPos(*position)
    world.attachRigidBody(node)
    return pointer


def shoulder_angles(origin, point, theta, transform=LMatrix3.identMat()):
    """Return the shoulder and elbow angles required to place the hand at the given point."""
    point -= origin
    point = transform.xform(point)

    l1, l2 = 0.75, 0.75
    q = point.normalized()
    dist = point.length()
    if dist > l1+l2:
        # cap the distance of the target to l1+l2
        dist = l1 + l2
        point = q * dist
    x, y, z = point

    # u1 and u2 form a basis for the plane perpendicular to OQ
    u1 = Vec3(z, 0, -x).normalized()
    u2 = Vec3(x*y, -x*x - z*z, y*z).normalized()

    sp = (dist+l1+l2)/2                                     # semi-perimeter of OPQ
    r = (2/dist)*math.sqrt(sp*(sp-dist)*(sp-l1)*(sp-l2))    # distance from OQ to P
    d = (dist**2 + l1**2 - l2**2)/(2*dist)                  # length of projection of OP onto OQ
    elbow = u1*r*math.cos(theta) + u2*r*math.sin(theta) + q*d

    # e1, e2, and e3 describe a rotation matrix
    e1 = elbow.normalized()
    e2 = (point - e1*point.dot(e1))
    if e2.length() < 1e-06:
        e2 = Vec3(-e1[2], 0, e1[0]).normalized()
    else:
        e2 = e2.normalized()
    e3 = e1.cross(e2)

    # alpha, beta, and gamma are the shoulder angles, while phi is the elbow angle
    alpha = math.atan2(e2[2], e2[0])
    beta = math.atan2(e2[1], e2[0]/math.cos(alpha))
    gamma = math.atan2(-e3[1]/math.cos(beta), -e1[1]/math.cos(beta))
    phi = abs(math.acos((l1**2 + l2**2 - dist**2)/(2*l1*l2)) - math.pi)

    return -gamma, beta, alpha, phi


class Arm(object):
    def __init__(self, world, render, side, torso, limits):
        radius = 0.15
        shoulder_space = 0.05
        bicep_length = 0.75
        forearm_length = 0.75
        in_limit, out_limit, forward_limit, backward_limit, twist_limit = limits
        shoulder_pos = Vec3(0, -side*(0.5+shoulder_space+radius), 0.5)
        bicep_pos = shoulder_pos + Vec3(0, -side * bicep_length / 2, 0)
        elbow_pos = shoulder_pos + Vec3(0, -side * bicep_length, 0)
        forearm_pos = elbow_pos + Vec3(0, -side * forearm_length / 2, 0)

        bicep = make_body('Bicep', 'capsule_y', [radius, bicep_length], 0.25, bicep_pos, torso, world)
        forearm = make_body('Forearm', 'capsule_y', [radius, forearm_length], 0.25, forearm_pos, torso, world)

        rotation = LMatrix3(side, 0, 0, 0, 0, -side, 0, 1, 0)
        bicep_to_shoulder = shoulder_pos - bicep_pos
        torso_to_shoulder = shoulder_pos
        bicep_shoulder_frame = make_rigid_transform(rotation, bicep_to_shoulder)
        torso_shoulder_frame = make_rigid_transform(rotation, torso_to_shoulder)
        shoulder = BulletGenericConstraint(torso.node(), bicep.node(), torso_shoulder_frame, bicep_shoulder_frame, True)
        shoulder.setDebugDrawSize(0.3)
        world.attachConstraint(shoulder, True)

        elbow_axis = Vec3(0, 0, side)
        forearm_to_elbow = elbow_pos - forearm_pos
        bicep_to_elbow = elbow_pos - bicep_pos
        elbow = BulletHingeConstraint(bicep.node(), forearm.node(), bicep_to_elbow, forearm_to_elbow,
                                      elbow_axis, elbow_axis, True)
        elbow.setDebugDrawSize(0.3)
        world.attachConstraint(elbow, True)

        for axis in range(3):
            shoulder.getRotationalLimitMotor(axis).setMaxMotorForce(200)
        elbow.setMaxMotorImpulse(200)

        shoulder.setAngularLimit(0, -in_limit, out_limit)
        shoulder.setAngularLimit(1, -twist_limit, twist_limit)
        shoulder.setAngularLimit(2, -backward_limit, forward_limit)

        elbow.setLimit(0, 180)

        torso_xform = torso.getMat(render)
        self.position = torso_xform.xform(VBase4(shoulder_pos, 1)).getXyz()
        self.bicep = bicep
        self.forearm = forearm
        self.shoulder = shoulder
        self.elbow = elbow
        self.transform = (torso_xform * LMatrix3(1, 0, 0, 0, side, 0, 0, 0, 1)).getUpper3()
        self.side = side

        self.lines = LineNodePath(name='debug', parent=render, colorVec=VBase4(0.2, 0.2, 0.5, 1))

        axes = LineNodePath(name='axes', parent=render)
        paths = [dict(color=VBase4(1, 0, 0, 1)), dict(color=VBase4(0, 1, 0, 1)), dict(color=VBase4(0, 0, 1, 1))]
        for i in range(3):
            axis = shoulder.getAxis(i) * 0.25
            paths[i]['points'] = [axis]
        draw_lines(axes, *paths, origin=self.position)

    def set_shoulder_motion(self, axis, speed):
        """Set the shoulder motor along the given axis to the given speed."""
        motor = self.shoulder.getRotationalLimitMotor(axis)
        motor.setTargetVelocity(speed)
        motor.setMotorEnabled(True)
        self.bicep.node().setActive(True, False)

    def move_toward(self, x, y, z, theta, tol=0.01, dt=1.0):
        """Set shoulder and elbow motor velocities such that the hand moves toward the specified point."""
        shoulder_pos = Vec3(0, 0, 0)
        hand_pos = Vec3(x, y, z)
        target_angles = shoulder_angles(shoulder_pos, hand_pos, theta, self.transform)
        for axis in range(3):
            motor = self.shoulder.getRotationalLimitMotor(axis)
            angle = self.shoulder.getAngle(axis)
            diff = target_angles[axis] - angle
            if abs(diff) > tol:
                motor.setTargetVelocity(diff / dt)
            else:
                motor.setTargetVelocity(0)
            motor.setMotorEnabled(True)
        self.elbow.enableMotor(True)
        self.elbow.setMotorTarget(target_angles[3], dt)
        self.bicep.node().setActive(True, False)
        draw_lines(self.lines, dict(points=[hand_pos]), origin=self.position)

    def go_limp(self):
        for axis in range(3):
            self.shoulder.getRotationalLimitMotor(axis).setMotorEnabled(False)
        self.elbow.enableMotor(False)
        self.bicep.node().setActive(True, False)


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
        self.arm_l, self.arm_r = None, None

    @classmethod
    def from_json(cls, file):
        attributes = json.load(file)
        move_names = attributes.pop('basic_moves')
        move_set = [moves.moves[move_name] for move_name in move_names]
        return cls(attributes, char_moves=move_set)

    def insert(self, world, render, i, pos):
        # Important numbers
        head_radius = 0.5
        head_elevation = 1.5
        torso_x = 0.3
        torso_y = 0.5
        torso_z = 0.75
        torso_elevation = head_elevation - head_radius - torso_z

        x, y = pos
        offset = Vec3(x, y, 0)
        rotation = LMatrix3((-i, 0, 0), (0, -i, 0), (0, 0, 1))
        coord_xform = LMatrix4(rotation, offset)

        # measurements below are in degrees
        neck_yaw_limit = 90
        neck_pitch_limit = 45
        shoulder_twist_limit = 90  # limit for twisting arm along the bicep axis
        shoulder_in_limit = 175  # maximum declination from T-pose towards torso
        shoulder_out_limit = 90  # maximum elevation from T-pose away from torso
        shoulder_forward_limit = 175  # maximum angle from down by side to pointing forward
        shoulder_backward_limit = 90  # maximum angle from down by side to pointing backward

        # Create a torso
        torso_pos = Vec3(0, 0, torso_elevation)
        torso = make_body('Torso', 'box', [torso_x, torso_y, torso_z], 0, torso_pos, render, world)
        xform = TransformState.makeMat(coord_xform)
        torso.setTransform(torso, xform)

        # Create a head
        head_pos = Vec3(0, 0, head_elevation - torso_elevation)
        head = make_body('Head', 'sphere', [0.5], 1, head_pos, torso, world)

        # Attach the head to the torso
        head_frame = TransformState.makePosHpr(Point3(0, 0, -head_radius), Vec3(0, 0, -90))
        torso_frame = TransformState.makePosHpr(Point3(0, 0, torso_z), Vec3(0, 0, -90))
        neck = BulletConeTwistConstraint(head.node(), torso.node(), head_frame, torso_frame)
        neck.setDebugDrawSize(0.5)
        neck.setLimit(neck_pitch_limit, neck_pitch_limit, neck_yaw_limit)
        world.attachConstraint(neck)

        # Create arms
        limits = (shoulder_in_limit, shoulder_out_limit, shoulder_forward_limit, shoulder_backward_limit,
                  shoulder_twist_limit)
        arm_l = Arm(world, render, LEFT, torso, limits)
        arm_r = Arm(world, render, RIGHT, torso, limits)

        self.head = head
        self.torso = torso
        self.arm_l, self.arm_r = arm_l, arm_r

    def set_shoulder_motion(self, axis, speed):
        self.arm_l.set_shoulder_motion(axis, speed)
        self.arm_r.set_shoulder_motion(axis, speed)

    def position_shoulder(self, side, target):
        arm = getattr(self, 'arm_' + side)
        arm.move_toward(*target, 0)

    def arms_down(self):
        self.arm_l.go_limp()
        self.arm_r.go_limp()

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
