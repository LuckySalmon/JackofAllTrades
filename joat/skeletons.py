from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, TypedDict
from typing_extensions import NotRequired

from direct.directtools.DirectGeometry import LineNodePath
from direct.showbase import ShowBaseGlobal
from direct.task.Task import Task
from direct.task.TaskManagerGlobal import taskMgr
from panda3d.bullet import (
    BulletGenericConstraint,
    BulletHingeConstraint,
    BulletRigidBodyNode,
    BulletWorld,
)
from panda3d.core import LColor, Mat3, Mat4, NodePath, VBase3, Vec3

from . import physics

LEFT, RIGHT = -1, 1


class _PathInfo(TypedDict):
    points: list[VBase3]
    color: NotRequired[LColor]


def draw_lines(
    lines: LineNodePath,
    *paths: _PathInfo,
    origin: VBase3 | None = None,
) -> None:
    if origin is None:
        origin = lines.getCurrentPosition()
    lines.reset()
    for path in paths:
        if 'color' in path:
            lines.setColor(path['color'])
        points = path['points']
        lines.moveTo(origin)
        for point in points:
            lines.drawTo(origin + point)
    lines.create()


def shoulder_angles(
    target: VBase3,
    theta: float,
    transform: Mat3 | None = None,
    arm_lengths: tuple[float, float] = (0.5, 0.5),
) -> tuple[float, float, float, float]:
    """Return the shoulder and elbow angles required
    to place the hand at the given point.
    """
    l1, l2 = arm_lengths
    max_dist = l1 + l2
    if transform is not None:
        target = transform.xform(target)
    unit_target = target.normalized()

    dist = target.length()
    if dist > max_dist:
        dist = max_dist
        dist_squared = dist * dist
    else:
        dist_squared = target.length_squared()

    # u1 and u2 form a basis for a plane perpendicular to the shoulder-hand axis
    u1 = Vec3(target.z, 0, -target.x).normalized()
    u2 = unit_target.cross(u1)

    # semi-perimeter of shoulder-elbow-hand triangle
    sp = (dist + l1 + l2) / 2
    # distance from the shoulder-hand axis to the elbow
    r = (2 / dist) * math.sqrt(sp * (sp-dist) * (sp-l1) * (sp-l2))  # fmt: skip
    # length of projection of shoulder-elbow onto shoulder-hand
    d = (dist_squared + l1*l1 - l2*l2) / (2 * dist)  # fmt: skip
    elbow = u1*r*math.cos(theta) + u2*r*math.sin(theta) + unit_target*d  # fmt: skip

    # e1, e2, and e3 describe a rotation matrix
    e1 = elbow.normalized()
    if math.isclose(dist, max_dist):
        e2 = VBase3(-elbow.z, 0, elbow.x).normalized()
    else:
        e2 = (target - target.project(elbow)).normalized()
    e3 = e1.cross(e2)

    # alpha, beta, and gamma are the shoulder angles; phi is the elbow angle
    alpha = math.atan2(e2.z, e2.x)
    beta = math.atan2(e2.y, e2.x / math.cos(alpha))
    gamma = math.atan2(-e3.y, -e1.y)
    phi = math.acos((l1*l1 + l2*l2 - dist_squared) / (2 * l1 * l2))  # fmt: skip

    return -gamma, beta, alpha, math.pi - phi


@dataclass(kw_only=True, repr=False)
class ArmController:
    origin: VBase3
    shoulder: BulletGenericConstraint
    elbow: BulletHingeConstraint
    bicep: NodePath[BulletRigidBodyNode]
    forearm: NodePath[BulletRigidBodyNode]
    transform: Mat3
    speed: float  # proportional to maximum angular velocity of joint motors
    target_point: VBase3 | None = None
    target_angle: float = 0
    lines: LineNodePath = field(init=False)

    def __post_init__(self) -> None:
        render = ShowBaseGlobal.base.render
        self.lines = LineNodePath(
            name='debug', parent=render, colorVec=LColor(0.2, 0.2, 0.5, 1)
        )
        draw_lines(
            LineNodePath(name='axes', parent=render),
            {
                'points': [self.shoulder.get_axis(0) / 4],
                'color': LColor(1, 0, 0, 1),
            },
            {
                'points': [self.shoulder.get_axis(1) / 4],
                'color': LColor(0, 1, 0, 1),
            },
            {
                'points': [self.shoulder.get_axis(2) / 4],
                'color': LColor(0, 0, 1, 1),
            },
            origin=self.origin,
        )

    def enable_motors(self, enabled: bool) -> None:
        for axis in range(3):
            motor = self.shoulder.get_rotational_limit_motor(axis)
            motor.set_motor_enabled(enabled)
        self.elbow.enable_motor(enabled)

    def set_target_shoulder_angle(self, axis: int, angle: float) -> None:
        motor = self.shoulder.get_rotational_limit_motor(axis)
        diff = angle - motor.current_position
        motor.set_target_velocity(diff * self.speed)

    def set_target_elbow_angle(self, angle: float) -> None:
        self.elbow.set_motor_target(angle, 1 / self.speed)

    def move(self, task: Task) -> int:
        """Move toward the position described
        by `target_point` and `target_angle`.
        """
        if self.target_point is None:
            return task.cont
        target_angles = shoulder_angles(
            self.target_point, self.target_angle, self.transform
        )
        for axis in range(3):
            self.set_target_shoulder_angle(axis, target_angles[axis])
        self.set_target_elbow_angle(target_angles[3])
        self.bicep.node().set_active(True)
        draw_lines(
            self.lines, {'points': [self.target_point]}, origin=self.origin
        )
        return task.cont


@dataclass(repr=False)
class Skeleton:
    parts: dict[str, NodePath[BulletRigidBodyNode]]
    arm_controllers: dict[int, ArmController] = field(kw_only=True)

    @classmethod
    def construct(
        cls,
        parameters: dict[str, dict[str, dict[str, Any]]],
        world: BulletWorld,
        coord_xform: Mat4,
        speed: float,
        strength: float,
    ) -> Skeleton:
        parts: dict[str, NodePath] = {}
        arm_controllers: dict[int, ArmController] = {}

        bodies = parameters['bodies']
        constraints = parameters['constraints']
        render = ShowBaseGlobal.base.render

        # Create a torso
        torso_data = bodies['torso']
        torso = physics.make_body(
            'Torso', **torso_data, parent=render, world=world
        )
        torso.set_mat(torso, coord_xform)
        parts['torso'] = torso

        # Create a head
        head_data = bodies['head']
        head = physics.make_body(
            'Head', **head_data, parent=torso, world=world
        )
        head.python_tags['damage_multiplier'] = 2
        parts['head'] = head

        # Attach the head to the torso
        neck_params = constraints['neck']
        neck_pos = Vec3(*neck_params['position'])
        neck = physics.make_cone_joint(neck_pos, torso, head, Vec3(0, 0, -90))
        # 0 softness means even small displacements are resisted
        neck.set_limit(*neck_params['limits'], softness=0)
        world.attach_constraint(neck)

        # Create arms
        for side, string in zip((LEFT, RIGHT), ('left', 'right')):
            shoulder_data = constraints[string + ' shoulder']
            elbow_data = constraints[string + ' elbow']
            bicep_data = bodies[string + ' bicep']
            forearm_data = bodies[string + ' forearm']

            (
                in_limit,
                out_limit,
                forward_limit,
                backward_limit,
                twist_limit,
            ) = shoulder_data['limits']
            shoulder_pos = Vec3(*shoulder_data['position'])
            elbow_pos = Vec3(*elbow_data['position'])

            bicep = physics.make_body(
                'Bicep', **bicep_data, parent=torso, world=world
            )
            forearm = physics.make_body(
                'Forearm', **forearm_data, parent=torso, world=world
            )
            bicep.python_tags['damage_multiplier'] = 0.5
            forearm.python_tags['damage_multiplier'] = 0.5

            rotation = Mat3(side, 0, 0, 0, 0, -side, 0, 1, 0)
            shoulder = physics.make_ball_joint(
                shoulder_pos, torso, bicep, rotation
            )
            world.attach_constraint(shoulder, True)

            elbow = physics.make_hinge_joint(
                elbow_pos - bicep.get_pos(), bicep, forearm, Vec3(0, 0, side)
            )
            world.attach_constraint(elbow, True)

            for axis in range(3):
                motor = shoulder.get_rotational_limit_motor(axis)
                motor.set_max_motor_force(strength)
            elbow.set_max_motor_impulse(strength)

            # limits for moving toward torso from T-pose
            shoulder.set_angular_limit(0, -in_limit, out_limit)
            # limit for twisting along the bicep axis
            shoulder.set_angular_limit(1, -twist_limit, twist_limit)
            # limits for moving forward from down by side
            shoulder.set_angular_limit(2, -backward_limit, forward_limit)

            elbow.set_limit(*elbow_data['limits'])

            position = render.get_relative_point(torso, shoulder_pos)
            transform = coord_xform.get_upper_3() * Mat3(
                1, 0, 0, 0, side, 0, 0, 0, 1
            )

            parts['bicep_' + string] = bicep
            parts['forearm_' + string] = forearm
            arm_controller = ArmController(
                origin=position,
                shoulder=shoulder,
                elbow=elbow,
                bicep=bicep,
                forearm=forearm,
                transform=transform,
                speed=speed,
            )
            arm_controller.enable_motors(True)
            arm_controllers[side] = arm_controller

        return cls(parts, arm_controllers=arm_controllers)

    def __post_init__(self) -> None:
        for controller in self.arm_controllers.values():
            taskMgr.add(controller.move, f'move_arm_{id(controller)}')

    def get_shoulder_position(self, side: int) -> VBase3:
        arm_controller = self.arm_controllers[side]
        return arm_controller.origin

    def get_arm_target(self, side: int) -> Vec3:
        target = self.arm_controllers[side].target_point
        assert target is not None
        return Vec3(target)

    def set_arm_target(
        self, side: int, target: VBase3, relative: bool = True
    ) -> None:
        local_target = Vec3(target)
        if not relative:
            local_target -= self.get_shoulder_position(side)
        self.arm_controllers[side].target_point = local_target

    def kill(self) -> None:
        for arm_controller in self.arm_controllers.values():
            arm_controller.enable_motors(False)
        torso = self.parts['torso'].node()
        torso.set_mass(1.0)
        torso.set_active(True)
