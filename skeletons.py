import math
import json
from typing import Literal

from panda3d.bullet import (
    BulletConeTwistConstraint,
    BulletGenericConstraint,
    BulletHingeConstraint,
    BulletRigidBodyNode,
    BulletWorld,
)
from panda3d.core import (
    VBase3,
    Vec3,
    VBase4,
    Mat3,
    Mat4,
    TransformState,
    NodePath,
)
from direct.directtools.DirectGeometry import LineNodePath

import physics

enableSound = False
charList = ['regular', 'boxer', 'psycho', 'test']
LEFT, RIGHT = -1, 1
with open('data\\skeletons\\default.json') as f:
    default_parameters = json.load(f)


def draw_lines(lines: LineNodePath,
               *paths: dict[str, list[VBase3]],
               origin: VBase3 | None = None,
               relative: bool = True) -> None:
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


def shoulder_angles(origin: VBase3,
                    point: VBase3,
                    theta: float,
                    transform: Mat3 = Mat3.identMat()) -> tuple[float, float, float, float]:
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
    def __init__(self,
                 world: BulletWorld,
                 render: NodePath,
                 side: int,
                 torso: 'NodePath[BulletRigidBodyNode]',
                 skeleton: dict[str] = default_parameters):
        string = 'left' if side == LEFT else 'right'
        shoulder_data = skeleton['constraints'][string + ' shoulder']
        elbow_data = skeleton['constraints'][string + ' elbow']
        bicep_data = skeleton['bodies'][string + ' bicep']
        forearm_data = skeleton['bodies'][string + ' forearm']

        in_limit, out_limit, forward_limit, backward_limit, twist_limit = shoulder_data['limits']
        shoulder_pos = Vec3(*shoulder_data['position'])
        bicep_pos = Vec3(*bicep_data['position'])
        elbow_pos = Vec3(*elbow_data['position'])
        forearm_pos = Vec3(*forearm_data['position'])

        bicep = physics.make_body('Bicep', **bicep_data, parent=torso, world=world)
        forearm = physics.make_body('Forearm', **forearm_data, parent=torso, world=world)

        rotation = Mat3(side, 0, 0, 0, 0, -side, 0, 1, 0)
        bicep_to_shoulder = shoulder_pos - bicep_pos
        torso_to_shoulder = shoulder_pos
        bicep_shoulder_frame = physics.make_rigid_transform(rotation, bicep_to_shoulder)
        torso_shoulder_frame = physics.make_rigid_transform(rotation, torso_to_shoulder)
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

        shoulder.setAngularLimit(0, -in_limit, out_limit)               # limits for moving toward torso from T-pose
        shoulder.setAngularLimit(1, -twist_limit, twist_limit)          # limit for twisting along the bicep axis
        shoulder.setAngularLimit(2, -backward_limit, forward_limit)     # limits for moving forward from down by side

        elbow.setLimit(*elbow_data['limits'])

        torso_xform = torso.getMat(render)
        self.position = torso_xform.xform(VBase4(shoulder_pos, 1)).getXyz()
        self.bicep = bicep
        self.forearm = forearm
        self.shoulder = shoulder
        self.elbow = elbow
        self.transform = (torso_xform * Mat3(1, 0, 0, 0, side, 0, 0, 0, 1)).getUpper3()
        self.side = side

        self.lines = LineNodePath(name='debug', parent=render, colorVec=VBase4(0.2, 0.2, 0.5, 1))

        axes = LineNodePath(name='axes', parent=render)
        paths = [dict(color=VBase4(1, 0, 0, 1)), dict(color=VBase4(0, 1, 0, 1)), dict(color=VBase4(0, 0, 1, 1))]
        for i in range(3):
            axis = shoulder.getAxis(i) * 0.25
            paths[i]['points'] = [axis]
        draw_lines(axes, *paths, origin=self.position)

    def set_shoulder_motion(self, axis: int, speed: float) -> None:
        """Set the shoulder motor along the given axis to the given speed."""
        motor = self.shoulder.getRotationalLimitMotor(axis)
        motor.setTargetVelocity(speed)
        motor.setMotorEnabled(True)
        self.bicep.node().setActive(True, False)

    def move_toward(self, x: float, y: float, z: float, theta: float, tol=0.01, dt=1.0) -> None:
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

    def go_limp(self) -> None:
        for axis in range(3):
            self.shoulder.getRotationalLimitMotor(axis).setMotorEnabled(False)
        self.elbow.enableMotor(False)
        self.bicep.node().setActive(True, False)


class Skeleton(object):
    def __init__(self, parameters: dict[str] | None):
        if parameters is None:
            parameters = default_parameters
        self.parameters = parameters
        self.head = None
        self.torso = None
        self.arm_l, self.arm_r = None, None

    def insert(self,
               world: BulletWorld,
               render: NodePath,
               coord_xform: Mat4) -> None:
        """Place the skeleton in the world."""
        bodies = self.parameters['bodies']
        constraints = self.parameters['constraints']

        # Create a torso
        torso_data = bodies['torso']
        torso_pos = Vec3(*torso_data['position'])
        torso = physics.make_body('Torso', **torso_data, parent=render, world=world)
        xform = TransformState.makeMat(coord_xform)
        torso.setTransform(torso, xform)

        # Create a head
        head_data = bodies['head']
        head_pos = Vec3(*head_data['position'])
        head = physics.make_body('Head', **head_data, parent=torso, world=world)

        # Attach the head to the torso
        neck_params = constraints['neck']
        neck_pos = Vec3(*neck_params['position'])
        head_frame = TransformState.makePosHpr(neck_pos - head_pos, Vec3(0, 0, -90))
        torso_frame = TransformState.makePosHpr(neck_pos - torso_pos, Vec3(0, 0, -90))
        neck = BulletConeTwistConstraint(head.node(), torso.node(), head_frame, torso_frame)
        neck.setDebugDrawSize(0.5)
        neck.setLimit(*neck_params['limits'])
        world.attachConstraint(neck)

        # Create arms
        arm_l = Arm(world, render, LEFT, torso, self.parameters)
        arm_r = Arm(world, render, RIGHT, torso, self.parameters)

        self.head = head
        self.torso = torso
        self.arm_l, self.arm_r = arm_l, arm_r

    def set_shoulder_motion(self, axis: int, speed: float) -> None:
        self.arm_l.set_shoulder_motion(axis, speed)
        self.arm_r.set_shoulder_motion(axis, speed)

    def position_shoulder(self, side: Literal['l', 'r'], target: VBase3) -> None:
        arm = getattr(self, 'arm_' + side)
        arm.move_toward(*target, 0)

    def arms_down(self) -> None:
        self.arm_l.go_limp()
        self.arm_r.go_limp()

    def kill(self) -> None:
        self.torso.node().setMass(1.0)
        self.torso.node().setActive(True, False)
