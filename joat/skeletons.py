from __future__ import annotations

import enum
import math
from typing import Any, cast
from typing_extensions import Self

import attrs
from panda3d.bullet import (
    BulletBoxShape,
    BulletCapsuleShape,
    BulletConstraint,
    BulletGenericConstraint,
    BulletHingeConstraint,
    BulletRigidBodyNode,
    BulletSphereShape,
)
from panda3d.core import (
    AsyncTaskPause,
    ClockObject,
    LVecBase2,
    Mat3,
    NodePath,
    TransformState,
    VBase3,
    Vec3,
)

from . import arenas, control, physics, stances, tasks


class Side(enum.Enum):
    LEFT = enum.auto()
    RIGHT = enum.auto()


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


@attrs.define
class HingeJointController:
    constraint: BulletHingeConstraint
    target_angle: float = 0

    def set_motor_enabled(self, enabled: bool) -> None:
        self.constraint.enable_motor(enabled)

    def move(self, speed: float) -> None:
        self.constraint.set_motor_target(self.target_angle, 1 / speed)


@attrs.define
class BallJointController:
    constraint: BulletGenericConstraint
    target_angles: tuple[float, float, float] = (0, 0, 0)

    def set_motors_enabled(self, enabled: bool) -> None:
        for i in range(3):
            motor = self.constraint.get_rotational_limit_motor(i)
            motor.motor_enabled = enabled

    def move(self, speed: float) -> None:
        for i in range(3):
            motor = self.constraint.get_rotational_limit_motor(i)
            target_angle = self.target_angles[i]
            diff = target_angle - motor.current_position
            motor.set_target_velocity(diff * speed)


@attrs.define(kw_only=True, repr=False)
class Arm:
    origin: VBase3
    shoulder: BallJointController
    elbow: HingeJointController
    bicep: NodePath[BulletRigidBodyNode]
    forearm: NodePath[BulletRigidBodyNode]
    transform: Mat3
    speed: float  # proportional to maximum angular velocity of joint motors
    _enabled: bool = True

    def __attrs_post_init__(self) -> None:
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
            shoulder=BallJointController(shoulder),
            elbow=HingeJointController(elbow),
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
        self.shoulder.set_motors_enabled(value)
        self.elbow.set_motor_enabled(value)

    def set_target(self, point: VBase3, angle: float = 0) -> None:
        angles = shoulder_angles(
            self.transform.xform(point),
            angle,
            arm_lengths=(self.bicep_length, self.forearm_length),
        )
        self.shoulder.target_angles = angles[:3]
        self.elbow.target_angle = angles[3]

    async def move(self) -> None:
        """Move the arm."""
        self.enabled = True
        while self.enabled:
            await AsyncTaskPause(0)
            self.shoulder.move(self.speed)
            self.elbow.move(self.speed)
            self.bicep.node().active = True


@attrs.define(repr=False, kw_only=True)
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
        *,
        transform: TransformState = TransformState.make_identity(),
        speed: float,
        strength: float,
    ) -> Self:
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
        base_width = eye_level - head_radius - torso_height

        torso = physics.make_body(
            name='Torso',
            shape=BulletBoxShape(Vec3(arm_radius, torso_width / 2, torso_height / 2)),
            position=Vec3(0, 0, torso_center),
            mass=32,
        )
        torso.set_transform(torso, transform)
        base = physics.make_body(
            name='Base',
            shape=BulletBoxShape(Vec3(0.25, 0.25, base_width * 0.49)),
            position=Vec3(0, 0, -(torso_height + base_width) / 2),
            mass=1000,
            parent=torso,
        )
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
        base.node().python_tags['damage_multiplier'] = 0

        neck = physics.make_cone_joint(
            torso,
            head,
            position=Vec3(0, 0, torso_height / 2),
            axis=Vec3(0, 0, 1),
        )
        neck.set_limit(45, 45, 90, softness=0)
        waist = physics.make_slider_joint(
            torso, base, position=Vec3(0, 0, -torso_height / 2), axis=Vec3(0, 0, 1)
        )
        return cls(
            parts={
                'torso': torso,
                'head': head,
                'bicep_left': left_arm.bicep,
                'bicep_right': right_arm.bicep,
                'forearm_left': left_arm.forearm,
                'forearm_right': right_arm.forearm,
                'base': base,
            },
            joints={
                'neck': neck,
                'shoulder_left': left_arm.shoulder.constraint,
                'shoulder_right': right_arm.shoulder.constraint,
                'elbow_left': left_arm.elbow.constraint,
                'elbow_right': right_arm.elbow.constraint,
                'waist': waist,
            },
            core=torso,
            left_arm=left_arm,
            right_arm=right_arm,
        )

    def get_arm(self, side: Side) -> Arm:
        if side is Side.LEFT:
            return self.left_arm
        else:
            return self.right_arm

    def enter_arena(self, arena: arenas.Arena) -> None:
        self.assume_stance()
        tasks.add_task(self.left_arm.move())
        tasks.add_task(self.right_arm.move())
        self.core.reparent_to(arena.root)
        for part in self.parts.values():
            arena.world.attach(part.node())
        for name, joint in self.joints.items():
            if name == 'neck' or name == 'waist':
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

    async def slide_to(self, target: LVecBase2, *, tol: float = 0.1) -> None:
        clock = ClockObject.get_global_clock()
        t0 = clock.frame_time
        base = self.parts['base']
        controller = control.pid(100, 1, 10, zero=LVecBase2)
        next(controller)
        while True:
            t1 = clock.frame_time
            here = self.core.get_pos().xy
            if here.almost_equal(target, threshold=tol):
                break
            impulse = controller.send((target - here, t1 - t0))
            base.node().apply_central_impulse(Vec3(impulse, 0))
            t0 = t1
            await AsyncTaskPause(0)

    def kill(self) -> None:
        self.left_arm.enabled = False
        self.right_arm.enabled = False
        for joint in self.joints.values():
            joint.enabled = False
