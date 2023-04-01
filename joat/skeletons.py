from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, cast

from panda3d.bullet import (
    BulletBoxShape,
    BulletCapsuleShape,
    BulletConstraint,
    BulletGenericConstraint,
    BulletHingeConstraint,
    BulletRigidBodyNode,
    BulletSphereShape,
)
from panda3d.core import AsyncTaskPause, Mat3, Mat4, NodePath, VBase3, Vec3

from . import arenas, physics, stances, tasks


def shoulder_angles(
    target: VBase3,
    theta: float,
    *,
    arm_lengths: tuple[float, float] = (0.5, 0.5),
) -> tuple[float, float, float, float]:
    """Return the shoulder and elbow angles required
    to place the hand at the given point.
    """
    l1, l2 = arm_lengths
    max_dist = l1 + l2
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
    target_shoulder_angles: tuple[float, float, float] = (0, 0, 0)
    target_elbow_angle: float = 0
    _enabled: bool = True

    def __post_init__(self) -> None:
        self.enabled = self._enabled

    @classmethod
    def construct(
        cls,
        origin: VBase3,
        *,
        length: float,
        radius: float,
        parent: NodePath,
        transform: Mat3,
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
        )
        forearm = physics.make_body(
            name='Forearm',
            shape=BulletCapsuleShape(radius, length / 2, up=1),
            position=along / 2,
            mass=5,
            parent=bicep,
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

        return cls(
            origin=origin,
            shoulder=shoulder,
            elbow=elbow,
            bicep=bicep,
            forearm=forearm,
            transform=transform,
            speed=speed,
        )

    @property
    def bicep_length(self) -> float:
        bicep_shape = cast(BulletCapsuleShape, self.bicep.node().shapes[0])
        return bicep_shape.height

    @property
    def forearm_length(self) -> float:
        forearm_shape = cast(BulletCapsuleShape, self.forearm.node().shapes[0])
        return forearm_shape.height

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value
        for axis in range(3):
            motor = self.shoulder.get_rotational_limit_motor(axis)
            motor.set_motor_enabled(value)
        self.elbow.enable_motor(value)

    def set_target(self, point: VBase3, angle: float = 0) -> None:
        angles = shoulder_angles(
            self.transform.xform(point),
            angle,
            arm_lengths=(self.bicep_length, self.forearm_length),
        )
        self.target_shoulder_angles = angles[:3]
        self.target_elbow_angle = angles[3]

    async def move(self) -> None:
        """Move the arm."""
        self.enabled = True
        while self.enabled:
            await AsyncTaskPause(0)
            for axis, angle in enumerate(self.target_shoulder_angles):
                motor = self.shoulder.get_rotational_limit_motor(axis)
                diff = angle - motor.current_position
                motor.set_target_velocity(diff * self.speed)
            self.elbow.set_motor_target(self.target_elbow_angle, 1 / self.speed)
            self.bicep.node().active = True


@dataclass(repr=False, kw_only=True)
class Skeleton:
    parts: dict[str, NodePath[BulletRigidBodyNode]]
    joints: dict[str, BulletConstraint]
    core: NodePath
    left_arm: Arm
    right_arm: Arm
    stance: stances.Stance = stances.T_POSE

    @classmethod
    def construct(
        cls,
        parameters: dict[str, dict[str, Any]],
        coord_xform: Mat4,
        speed: float,
        strength: float,
    ) -> Skeleton:
        measures: dict[str, float] = parameters['measures']
        head_radius = measures['head_radius']
        arm_length = measures['arm_length']
        arm_radius = measures['arm_radius']
        shoulder_width = measures['shoulder_width']
        torso_height = measures['torso_height']
        eye_level = measures['eye_level']
        torso_width = shoulder_width - 2 * arm_radius
        shoulder_height = torso_height / 2 - arm_radius
        shoulder_pos_l = Vec3(0, +shoulder_width / 2, shoulder_height)
        shoulder_pos_r = Vec3(0, -shoulder_width / 2, shoulder_height)
        torso_center = eye_level - head_radius - torso_height / 2

        torso = physics.make_body(
            name='Torso',
            shape=BulletBoxShape(Vec3(arm_radius, torso_width / 2, torso_height / 2)),
            position=Vec3(0, 0, torso_center),
            mass=0,
        )
        torso.set_mat(torso, coord_xform)
        head = physics.make_body(
            name='Head',
            shape=BulletSphereShape(head_radius),
            position=Vec3(0, 0, torso_height / 2 + head_radius),
            mass=16,
            parent=torso,
        )
        left_arm = Arm.construct(
            shoulder_pos_l,
            length=arm_length,
            radius=arm_radius,
            parent=torso,
            speed=speed,
            strength=strength,
            transform=Mat3(1, 0, 0, 0, -1, 0, 0, 0, 1),
        )
        right_arm = Arm.construct(
            shoulder_pos_r,
            length=arm_length,
            radius=arm_radius,
            parent=torso,
            speed=speed,
            strength=strength,
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
            core=torso,
            left_arm=left_arm,
            right_arm=right_arm,
        )

    def enter_arena(self, arena: arenas.Arena) -> None:
        self.assume_stance()
        tasks.add_task(self.left_arm.move())
        tasks.add_task(self.right_arm.move())
        self.core.reparent_to(arena.root)
        for part in self.parts.values():
            arena.world.attach(part.node())
        for name, joint in self.joints.items():
            if name == 'neck':
                arena.world.attach(joint)
            else:
                arena.world.attach_constraint(joint, linked_collision=True)

    def exit_arena(self, arena: arenas.Arena) -> None:
        self.left_arm.enabled = False
        self.right_arm.enabled = False
        self.core.detach_node()
        for joint in self.joints.values():
            arena.world.remove(joint)
        for part in self.parts.values():
            arena.world.remove(part.node())
            if part.python_tags:
                part.python_tags.clear()

    def assume_stance(self) -> None:
        self.left_arm.set_target(
            self.stance.left_hand_pos, self.stance.left_arm_angle  # fmt: skip
        )
        self.right_arm.set_target(
            self.stance.right_hand_pos, self.stance.right_arm_angle
        )

    def kill(self) -> None:
        self.left_arm.enabled = False
        self.right_arm.enabled = False
        for joint in self.joints.values():
            joint.enabled = False
