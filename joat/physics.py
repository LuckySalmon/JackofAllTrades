from __future__ import annotations

import math
from collections.abc import Callable, Iterable
from functools import partial

from direct.showbase import ShowBaseGlobal
from direct.task.Task import Task
from panda3d.bullet import (
    BulletBoxShape,
    BulletCapsuleShape,
    BulletConeTwistConstraint,
    BulletGenericConstraint,
    BulletHingeConstraint,
    BulletPlaneShape,
    BulletRigidBodyNode,
    BulletShape,
    BulletSphereShape,
    BulletWorld,
)
from panda3d.core import (
    CollideMask,
    Mat3,
    Mat4,
    NodePath,
    Quat,
    TransformState,
    VBase3,
    Vec3,
)

shape_constructors: dict[str, Callable[..., BulletShape]] = {
    'sphere': BulletSphereShape,
    'box': lambda *args: BulletBoxShape(Vec3(*args)),
    'capsule_x': partial(BulletCapsuleShape, up=0),
    'capsule_y': partial(BulletCapsuleShape, up=1),
    'capsule_z': partial(BulletCapsuleShape, up=2),
}


def make_quaternion(angle: float, axis: VBase3) -> Quat:
    """Return a quaternion representing a rotation
    with the given characteristics.
    """
    half_radians = angle / 360 * math.pi
    cosine = math.cos(half_radians)
    sine = math.sin(half_radians)
    return Quat(cosine, axis.normalized() * sine)


def make_rigid_transform(rotation: Mat3, translation: VBase3) -> TransformState:
    """Return a TransformState comprising the given rotation
    followed by the given translation
    """
    return TransformState.make_mat(Mat4(rotation, translation))


def make_body(
    name: str,
    *,
    shape: str,
    dimensions: Iterable[float],
    mass: float,
    position: VBase3 | Iterable[float],
    parent: NodePath,
    world: BulletWorld,
    collision_mask: CollideMask | int = CollideMask.all_on(),
) -> NodePath[BulletRigidBodyNode]:
    """Return a NodePath for a new rigid body with the given characteristics"""
    constructor = shape_constructors[shape]
    node = BulletRigidBodyNode(name)
    node.add_shape(constructor(*dimensions))
    node.set_mass(mass)
    path = parent.attach_new_node(node)
    path.set_pos(*position)
    path.set_collide_mask(CollideMask(collision_mask))
    world.attach(node)
    return path


def make_ball_joint(
    position: VBase3,
    node_path_a: NodePath,
    node_path_b: NodePath,
    rotation: Mat3,
) -> BulletGenericConstraint:
    a_to_joint = position
    b_to_joint = node_path_b.get_relative_point(node_path_a, position)
    frame_a = make_rigid_transform(rotation, a_to_joint)
    frame_b = make_rigid_transform(rotation, b_to_joint)
    joint = BulletGenericConstraint(
        node_path_a.node(), node_path_b.node(), frame_a, frame_b, True
    )
    return joint


def make_hinge_joint(
    position: VBase3, node_path_a: NodePath, node_path_b: NodePath, axis: Vec3
) -> BulletHingeConstraint:
    a_to_joint = position
    b_to_joint = node_path_b.get_relative_point(node_path_a, position)
    joint = BulletHingeConstraint(
        node_path_a.node(),
        node_path_b.node(),
        a_to_joint,
        b_to_joint,
        axis,
        axis,
        True,
    )
    return joint


def make_cone_joint(
    position: VBase3, node_path_a: NodePath, node_path_b: NodePath, hpr: VBase3
) -> BulletConeTwistConstraint:
    a_to_joint = position
    b_to_joint = node_path_b.get_relative_point(node_path_a, position)
    frame_a = TransformState.make_pos_hpr(a_to_joint, hpr)
    frame_b = TransformState.make_pos_hpr(
        b_to_joint, node_path_b.get_relative_vector(node_path_a, hpr)
    )
    joint = BulletConeTwistConstraint(
        node_path_a.node(), node_path_b.node(), frame_a, frame_b
    )
    return joint


def make_world(*, gravity: VBase3) -> BulletWorld:
    world = BulletWorld()
    world.set_gravity(gravity)
    ground_node = BulletRigidBodyNode('Ground')
    ground_node.add_shape(BulletPlaneShape(Vec3(0, 0, 1), 1))
    ground_node_path = ShowBaseGlobal.base.render.attach_new_node(ground_node)
    ground_node_path.set_pos(0, 0, -2)
    world.attach(ground_node)
    return world


def update_physics(world: BulletWorld, task: Task) -> int:
    dt = ShowBaseGlobal.globalClock.get_dt()
    world.do_physics(dt)
    return task.cont
