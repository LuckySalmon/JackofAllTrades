import math
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from panda3d.bullet import (
    BulletWorld,
    BulletGenericConstraint,
    BulletHingeConstraint,
    BulletRigidBodyNode
)
from panda3d.core import (
    VBase3,
    Vec3,
    VBase4,
    Mat3,
    Mat4,
    NodePath,
)
from direct.directtools.DirectGeometry import LineNodePath
from direct.task.Task import Task
from direct.task.TaskManagerGlobal import taskMgr
from direct.showbase import ShowBaseGlobal

from . import physics

enableSound = False
charList = ['regular', 'boxer', 'psycho', 'test']
LEFT, RIGHT = -1, 1
with Path('data', 'skeletons', 'default.json').open() as f:
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
        lines.moveTo(origin)
        for point in points:
            if relative:
                point += origin
            lines.drawTo(point)
    lines.create()


def shoulder_angles(
    target: VBase3,
    theta: float,
    transform: Mat3 = Mat3(),
    arm_lengths: tuple[float, float] = (0.75, 0.75),
) -> tuple[float, float, float, float]:
    """Return the shoulder and elbow angles required
    to place the hand at the given point.
    """
    l1, l2 = arm_lengths
    target = transform.xform(target)
    unit_target = target.normalized()

    dist = target.length()
    if dist > (max_dist := l1+l2):
        # cap the distance of the target to l1+l2
        dist = max_dist
        target = unit_target * dist
        dist_squared = dist * dist
    else:
        dist_squared = target.length_squared()

    # u1 and u2 form a basis for a plane perpendicular to the shoulder-hand axis
    u1 = Vec3(target.z, 0, -target.x).normalized()
    u2 = unit_target.cross(u1)

    # semi-perimeter of shoulder-elbow-hand triangle
    sp = (dist + l1 + l2) / 2
    # distance from the shoulder-hand axis to the elbow
    r = (2 / dist) * math.sqrt(sp * (sp-dist) * (sp-l1) * (sp-l2))
    # length of projection of shoulder-elbow onto shoulder-hand
    d = (dist_squared + l1*l1 - l2*l2) / (2 * dist)
    elbow = u1*r*math.cos(theta) + u2*r*math.sin(theta) + unit_target*d

    # e1, e2, and e3 describe a rotation matrix
    e1 = elbow.normalized()
    if e1.almost_equal(unit_target):
        e2 = Vec3(-elbow.z, 0, elbow.x).normalized()
    else:
        e2 = (target - target.project(elbow)).normalized()
    e3 = e1.cross(e2)

    # alpha, beta, and gamma are the shoulder angles; phi is the elbow angle
    alpha = math.atan2(e2.z, e2.x)
    beta = math.atan2(e2.y, e2.x / math.cos(alpha))
    gamma = math.atan2(-e3.y, -e1.y)
    phi = math.acos((l1*l1 + l2*l2 - dist_squared) / (2 * l1 * l2))

    return -gamma, beta, alpha, math.pi - phi


@dataclass
class ArmController:
    origin: VBase3
    shoulder: BulletGenericConstraint
    elbow: BulletHingeConstraint
    bicep: 'NodePath[BulletRigidBodyNode]'
    forearm: 'NodePath[BulletRigidBodyNode]'
    transform: Mat3
    speed: float  # proportional to maximum angular velocity of joint motors

    def __post_init__(self):
        render = ShowBaseGlobal.base.render

        self.lines = LineNodePath(name='debug', parent=render,
                                  colorVec=VBase4(0.2, 0.2, 0.5, 1))
        axes = LineNodePath(name='axes', parent=render)
        paths: list[dict[str, Any]] = [dict(color=VBase4(1, 0, 0, 1)),
                                       dict(color=VBase4(0, 1, 0, 1)),
                                       dict(color=VBase4(0, 0, 1, 1))]
        for i in range(3):
            axis = self.shoulder.get_axis(i) * 0.25
            paths[i]['points'] = [axis]
        draw_lines(axes, *paths, origin=self.origin)

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

    def move_toward(self, x: float, y: float, z: float, theta: float) -> None:
        """Set shoulder and elbow motor velocities such that
        the hand moves toward the specified point.
        """
        hand_pos = Vec3(x, y, z)
        target_angles = shoulder_angles(hand_pos, theta, self.transform)
        for axis in range(3):
            self.set_target_shoulder_angle(axis, target_angles[axis])
        self.set_target_elbow_angle(target_angles[3])
        self.bicep.node().set_active(True, False)
        draw_lines(self.lines, dict(points=[hand_pos]), origin=self.origin)


@dataclass
class Skeleton:
    parts: 'dict[str, NodePath[BulletRigidBodyNode]]'
    arm_controllers: dict[int, ArmController]
    arm_targets: dict[int, Vec3 | None] = field(
        default_factory=lambda: {LEFT: None, RIGHT: None}
    )
    targeting: bool = field(default=True, init=False)

    @classmethod
    def construct(cls,
                  parameters: dict[str, dict[str, dict[str, Any]]],
                  world: BulletWorld,
                  coord_xform: Mat4,
                  speed: float,
                  strength: float) -> 'Skeleton':
        parts: dict[str, NodePath] = {}
        arm_controllers: dict[int, ArmController] = {}

        bodies = parameters['bodies']
        constraints = parameters['constraints']
        render = ShowBaseGlobal.base.render

        # Create a torso
        torso_data = bodies['torso']
        torso = physics.make_body('Torso', **torso_data, parent=render, world=world)
        torso.set_mat(torso, coord_xform)
        parts['torso'] = torso

        # Create a head
        head_data = bodies['head']
        head = physics.make_body('Head', **head_data, parent=torso, world=world)
        parts['head'] = head

        # Attach the head to the torso
        neck_params = constraints['neck']
        neck_pos = Vec3(*neck_params['position'])
        neck = physics.make_cone_joint(neck_pos, torso, head, Vec3(0, 0, -90))
        neck.setLimit(*neck_params['limits'])
        world.attach_constraint(neck)

        # Create arms
        for side, string in zip((LEFT, RIGHT), ('left', 'right')):
            shoulder_data = constraints[string + ' shoulder']
            elbow_data = constraints[string + ' elbow']
            bicep_data = bodies[string + ' bicep']
            forearm_data = bodies[string + ' forearm']

            in_limit, out_limit, forward_limit, backward_limit, twist_limit = shoulder_data['limits']
            shoulder_pos = Vec3(*shoulder_data['position'])
            elbow_pos = Vec3(*elbow_data['position'])

            bicep = physics.make_body('Bicep', **bicep_data,
                                      parent=torso, world=world)
            forearm = physics.make_body('Forearm', **forearm_data,
                                        parent=torso, world=world)

            rotation = Mat3(side, 0, 0, 0, 0, -side, 0, 1, 0)
            shoulder = physics.make_ball_joint(shoulder_pos, torso,
                                               bicep, rotation)
            world.attach_constraint(shoulder, True)

            elbow = physics.make_hinge_joint(elbow_pos - bicep.get_pos(),
                                             bicep, forearm, Vec3(0, 0, side))
            world.attach_constraint(elbow, True)

            for axis in range(3):
                shoulder.get_rotational_limit_motor(axis).set_max_motor_force(strength)
            elbow.set_max_motor_impulse(strength)

            # limits for moving toward torso from T-pose
            shoulder.set_angular_limit(0, -in_limit, out_limit)
            # limit for twisting along the bicep axis
            shoulder.set_angular_limit(1, -twist_limit, twist_limit)
            # limits for moving forward from down by side
            shoulder.set_angular_limit(2, -backward_limit, forward_limit)

            elbow.set_limit(*elbow_data['limits'])

            position = render.get_relative_point(torso, shoulder_pos)
            transform = coord_xform.get_upper_3() * Mat3(1, 0, 0,
                                                         0, side, 0,
                                                         0, 0, 1)

            parts['bicep_' + string] = bicep
            parts['forearm_' + string] = forearm
            arm_controller = ArmController(position, shoulder, elbow,
                                           bicep, forearm, transform, speed)
            arm_controller.enable_motors(True)
            arm_controllers[side] = arm_controller

        return cls(parts, arm_controllers)

    def __post_init__(self):
        taskMgr.add(self.move_arms, f'move_arms_{id(self)}')

    def get_shoulder_position(self, side: int) -> VBase3:
        arm_controller = self.arm_controllers[side]
        return arm_controller.origin

    def position_shoulder(self, side: int, target: VBase3) -> None:
        arm_controller = self.arm_controllers[side]
        arm_controller.move_toward(*target, 0)

    def get_arm_target(self, side: int) -> Vec3:
        return Vec3(self.arm_targets[side])

    def set_arm_target(self, side: int, target: VBase3,
                       relative: bool = True) -> None:
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
        torso.set_mass(1.0)
        torso.set_active(True, False)
