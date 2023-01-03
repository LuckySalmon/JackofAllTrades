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
    BulletBoxShape,
    BulletCapsuleShape,
    BulletConstraint,
    BulletGenericConstraint,
    BulletHingeConstraint,
    BulletRigidBodyNode,
    BulletSphereShape,
    BulletWorld,
)
from panda3d.core import LColor, Mat3, Mat4, NodePath, VBase3, Vec3

from . import physics, stances


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
class Arm:
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

    @classmethod
    def construct(
        cls,
        origin: VBase3,
        *,
        length: float,
        radius: float,
        parent: NodePath,
        transform: Mat3,
        world: BulletWorld,
        speed: float = 1,
        strength: float = 1,
    ) -> Arm:
        along = transform.xform(Vec3(0, -length, 0))
        shoulder_transform = Mat3(1, 0, 0, 0, 0, -1, 0, 1, 0)
        elbow_axis = Vec3(0, 0, 1)
        if transform.determinant() < 0:
            # The arm is reflected, so we need to invert the rotation axes.
            # I wasn't able to fully wrap my head around why.
            shoulder_transform *= -1
            elbow_axis *= -1
        bicep = physics.make_body(
            name='Bicep',
            shape=BulletCapsuleShape(radius, length / 2, up=1),
            position=origin + along / 4,
            mass=5,
            parent=parent,
            world=world,
        )
        forearm = physics.make_body(
            name='Forearm',
            shape=BulletCapsuleShape(radius, length / 2, up=1),
            position=along / 2,
            mass=5,
            parent=bicep,
            world=world,
        )
        shoulder = physics.make_ball_joint(
            parent, bicep, position=origin, rotation=shoulder_transform
        )
        elbow = physics.make_hinge_joint(
            bicep, forearm, position=along / 4, axis=elbow_axis
        )

        for axis in range(3):
            shoulder.get_rotational_limit_motor(axis).set_max_motor_force(strength)
        elbow.set_max_motor_impulse(strength)
        elbow.set_limit(0, 180)
        # limits for moving outward from down by side
        shoulder.set_angular_limit(0, -175, 90)
        # limit for twisting along the bicep axis
        shoulder.set_angular_limit(1, -90, 90)
        # limits for moving forward from down by side
        shoulder.set_angular_limit(2, -90, 175)

        world.attach_constraint(shoulder, linked_collision=True)
        world.attach_constraint(elbow, linked_collision=True)

        return cls(
            origin=origin,
            shoulder=shoulder,
            elbow=elbow,
            bicep=bicep,
            forearm=forearm,
            transform=transform,
            speed=speed,
        )

    def __post_init__(self) -> None:
        self.lines = LineNodePath(
            name='debug', parent=self.bicep.parent, colorVec=LColor(0.2, 0.2, 0.5, 1)
        )
        draw_lines(
            LineNodePath(name='axes', parent=self.bicep.parent),
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
        draw_lines(self.lines, {'points': [self.target_point]}, origin=self.origin)
        return task.cont


@dataclass(repr=False, kw_only=True)
class Skeleton:
    parts: dict[str, NodePath[BulletRigidBodyNode]]
    joints: dict[str, BulletConstraint]
    left_arm: Arm
    right_arm: Arm
    stance: stances.Stance = stances.T_POSE
    transform: Mat4 = Mat4.ident_mat()

    @classmethod
    def construct(
        cls,
        parameters: dict[str, dict[str, Any]],
        world: BulletWorld,
        coord_xform: Mat4,
        speed: float,
        strength: float,
    ) -> Skeleton:
        render = ShowBaseGlobal.base.render
        measures: dict[str, float] = parameters['measures']
        head_radius = measures['head_radius']
        arm_length = measures['arm_length']
        arm_radius = measures['arm_radius']
        shoulder_width = measures['shoulder_width']
        torso_height = measures['torso_height']
        torso_width = shoulder_width - 2 * arm_radius
        shoulder_height = torso_height / 2 - arm_radius
        shoulder_pos_l = Vec3(0, +shoulder_width / 2, shoulder_height)
        shoulder_pos_r = Vec3(0, -shoulder_width / 2, shoulder_height)

        torso = physics.make_body(
            name='Torso',
            shape=BulletBoxShape(Vec3(arm_radius, torso_width / 2, torso_height / 2)),
            position=Vec3(0, 0, 0.25),
            mass=0,
            parent=render,
            world=world,
        )
        torso.set_mat(torso, coord_xform)
        head = physics.make_body(
            name='Head',
            shape=BulletSphereShape(head_radius),
            position=Vec3(0, 0, torso_height / 2 + head_radius),
            mass=16,
            parent=torso,
            world=world,
        )
        left_arm = Arm.construct(
            shoulder_pos_l,
            length=arm_length,
            radius=arm_radius,
            parent=torso,
            speed=speed,
            strength=strength,
            world=world,
            transform=Mat3(1, 0, 0, 0, -1, 0, 0, 0, 1),
        )
        right_arm = Arm.construct(
            shoulder_pos_r,
            length=arm_length,
            radius=arm_radius,
            parent=torso,
            speed=speed,
            strength=strength,
            world=world,
            transform=Mat3(1, 0, 0, 0, +1, 0, 0, 0, 1),
        )

        head.node().python_tags['damage_multiplier'] = 2
        left_arm.bicep.node().python_tags['damage_multiplier'] = 0.5
        right_arm.bicep.node().python_tags['damage_multiplier'] = 0.5
        left_arm.forearm.node().python_tags['damage_multiplier'] = 0.5
        right_arm.forearm.node().python_tags['damage_multiplier'] = 0.5

        neck = physics.make_cone_joint(
            torso,
            head,
            position=Vec3(0, 0, torso_height / 2),
            rotation=Mat3(0, 0, 1, 0, 1, 0, -1, 0, 0),
        )
        neck.set_limit(45, 45, 90, softness=0)
        world.attach_constraint(neck)
        left_arm.enable_motors(True)
        right_arm.enable_motors(True)
        return cls(
            parts={
                'torso': torso,
                'head': head,
                'bicep_left': left_arm.bicep,
                'bicep_right': right_arm.bicep,
                'forearm_left': left_arm.forearm,
                'forearm_right': right_arm.forearm,
            },
            joints={
                'neck': neck,
                'shoulder_left': left_arm.shoulder,
                'shoulder_right': right_arm.shoulder,
                'elbow_left': left_arm.elbow,
                'elbow_right': right_arm.elbow,
            },
            left_arm=left_arm,
            right_arm=right_arm,
            transform=coord_xform,
        )

    def __post_init__(self) -> None:
        self.assume_stance()
        taskMgr.add(self.left_arm.move, f'move_left_arm_{id(self)}')
        taskMgr.add(self.right_arm.move, f'move_right_arm_{id(self)}')

    def assume_stance(self) -> None:
        self.left_arm.target_point = self.stance.left_hand_pos
        self.right_arm.target_point = self.stance.right_hand_pos
        self.left_arm.target_angle = self.stance.left_arm_angle
        self.right_arm.target_angle = self.stance.right_arm_angle

    def kill(self) -> None:
        self.left_arm.enable_motors(False)
        self.right_arm.enable_motors(False)
        for joint in self.joints.values():
            joint.enabled = False
