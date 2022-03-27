import math
import json
from typing import Any

from panda3d.bullet import BulletWorld
from panda3d.core import (
    VBase3,
    Vec3,
    VBase4,
    Mat3,
    Mat4,
    TransformState,
)
from direct.directtools.DirectGeometry import LineNodePath
from direct.task.Task import Task
from direct.task.TaskManagerGlobal import taskMgr
from direct.showbase import ShowBaseGlobal

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


class ArmController:
    def __init__(self, origin, shoulder, elbow, bicep, forearm, transform, speed):
        self.origin = origin
        self.shoulder = shoulder
        self.elbow = elbow
        self.bicep = bicep
        self.forearm = forearm
        self.transform = transform
        self.speed = speed  # proportional to maximum angular velocity of joint motors
        render = ShowBaseGlobal.base.render

        self.lines = LineNodePath(name='debug', parent=render, colorVec=VBase4(0.2, 0.2, 0.5, 1))
        axes = LineNodePath(name='axes', parent=render)
        paths = [dict(color=VBase4(1, 0, 0, 1)), dict(color=VBase4(0, 1, 0, 1)), dict(color=VBase4(0, 0, 1, 1))]
        for i in range(3):
            axis = shoulder.getAxis(i) * 0.25
            paths[i]['points'] = [axis]
        draw_lines(axes, *paths, origin=self.origin)

    def enable_motors(self, enabled: bool) -> None:
        for axis in range(3):
            motor = self.shoulder.getRotationalLimitMotor(axis)
            motor.setMotorEnabled(enabled)
        self.elbow.enableMotor(enabled)

    def set_target_shoulder_angle(self, axis: int, angle: float) -> None:
        motor = self.shoulder.getRotationalLimitMotor(axis)
        diff = angle - motor.current_position
        motor.setTargetVelocity(diff * self.speed)

    def set_target_elbow_angle(self, angle: float) -> None:
        self.elbow.setMotorTarget(angle, 1 / self.speed)

    def move_toward(self, x: float, y: float, z: float, theta: float) -> None:
        """Set shoulder and elbow motor velocities such that the hand moves toward the specified point."""
        shoulder_pos = Vec3(0, 0, 0)
        hand_pos = Vec3(x, y, z)
        target_angles = shoulder_angles(shoulder_pos, hand_pos, theta, self.transform)
        for axis in range(3):
            self.set_target_shoulder_angle(axis, target_angles[axis])
        self.set_target_elbow_angle(target_angles[3])
        self.bicep.node().setActive(True, False)
        draw_lines(self.lines, dict(points=[hand_pos]), origin=self.origin)


class Skeleton:
    def __init__(self,
                 parameters: dict[str, Any],
                 world: BulletWorld,
                 coord_xform: Mat4,
                 speed: float,
                 strength: float):
        self.parts = {}
        self.arm_l, self.arm_r = None, None
        self.arm_controllers: dict[int, ArmController] = {}
        self.arm_targets: dict[int, Vec3 | None] = {LEFT: None, RIGHT: None}
        self.targeting = True

        bodies = parameters['bodies']
        constraints = parameters['constraints']
        render = ShowBaseGlobal.base.render

        # Create a torso
        torso_data = bodies['torso']
        torso = physics.make_body('Torso', **torso_data, parent=render, world=world)
        xform = TransformState.makeMat(coord_xform)
        torso.setTransform(torso, xform)

        # Create a head
        head_data = bodies['head']
        head = physics.make_body('Head', **head_data, parent=torso, world=world)

        # Attach the head to the torso
        neck_params = constraints['neck']
        neck_pos = Vec3(*neck_params['position'])
        neck = physics.make_cone_joint(neck_pos, torso, head, Vec3(0, 0, -90))
        neck.setDebugDrawSize(0.5)
        neck.setLimit(*neck_params['limits'])
        world.attachConstraint(neck)

        # Create arms
        for side, string in zip((LEFT, RIGHT), ('left', 'right')):
            shoulder_data = constraints[string + ' shoulder']
            elbow_data = constraints[string + ' elbow']
            bicep_data = bodies[string + ' bicep']
            forearm_data = bodies[string + ' forearm']

            in_limit, out_limit, forward_limit, backward_limit, twist_limit = shoulder_data['limits']
            shoulder_pos = Vec3(*shoulder_data['position'])
            elbow_pos = Vec3(*elbow_data['position'])

            bicep = physics.make_body('Bicep', **bicep_data, parent=torso, world=world)
            forearm = physics.make_body('Forearm', **forearm_data, parent=torso, world=world)

            rotation = Mat3(side, 0, 0, 0, 0, -side, 0, 1, 0)
            shoulder = physics.make_ball_joint(shoulder_pos, torso, bicep, rotation)
            shoulder.setDebugDrawSize(0.3)
            world.attachConstraint(shoulder, True)

            elbow = physics.make_hinge_joint(elbow_pos - bicep.getPos(), bicep, forearm, Vec3(0, 0, side))
            elbow.setDebugDrawSize(0.3)
            world.attachConstraint(elbow, True)

            for axis in range(3):
                shoulder.getRotationalLimitMotor(axis).setMaxMotorForce(strength)
            elbow.setMaxMotorImpulse(strength)

            shoulder.setAngularLimit(0, -in_limit, out_limit)            # limits for moving toward torso from T-pose
            shoulder.setAngularLimit(1, -twist_limit, twist_limit)       # limit for twisting along the bicep axis
            shoulder.setAngularLimit(2, -backward_limit, forward_limit)  # limits for moving forward from down by side

            elbow.setLimit(*elbow_data['limits'])

            torso_xform = torso.getMat()
            position = torso_xform.xform(VBase4(shoulder_pos, 1)).getXyz()
            transform = coord_xform.getUpper3() * Mat3(1, 0, 0, 0, side, 0, 0, 0, 1)

            self.parts[f'bicep_{string}'] = bicep
            self.parts[f'forearm_{string}'] = forearm
            arm_controller = ArmController(position, shoulder, elbow, bicep, forearm, transform, speed)
            arm_controller.enable_motors(True)
            self.arm_controllers[side] = arm_controller

        self.parts['torso'] = torso
        self.parts['head'] = head

        taskMgr.add(self.move_arms, f'move_arms_{id(self)}')

    def get_shoulder_position(self, side: int) -> VBase3:
        arm_controller = self.arm_controllers[side]
        point = arm_controller.shoulder.getFrameA().getPos()
        xform = self.parts['torso'].getNetTransform()
        return xform.getMat().xformPoint(point)

    def position_shoulder(self, side: int, target: VBase3) -> None:
        arm_controller = self.arm_controllers[side]
        arm_controller.move_toward(*target, 0)

    def get_arm_target(self, side: int) -> Vec3:
        return Vec3(self.arm_targets[side])

    def set_arm_target(self, side: int, target: VBase3, relative: bool = True) -> None:
        local_target = Vec3(target)
        if not relative:
            local_target -= self.get_shoulder_position(side)
        self.arm_targets[side] = local_target

    def move_arms(self, task: Task) -> int:
        if self.targeting:
            for side in LEFT, RIGHT:
                target = self.arm_targets[side]
                if target is not None:
                    self.position_shoulder(side, target)
        return task.cont

    def toggle_targeting(self) -> None:
        self.targeting = not self.targeting

    def kill(self) -> None:
        for arm_controller in self.arm_controllers.values():
            arm_controller.enable_motors(False)
        torso = self.parts['torso'].node()
        torso.setMass(1.0)
        torso.setActive(True, False)
