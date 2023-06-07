from __future__ import annotations

import logging
import math
from typing import Final

from panda3d.bullet import (
    BulletConeTwistConstraint,
    BulletGenericConstraint,
    BulletHingeConstraint,
    BulletPersistentManifold,
    BulletRigidBodyNode,
    BulletShape,
    BulletSliderConstraint,
    BulletSphereShape,
    BulletWorld,
)
from panda3d.core import CollideMask, Mat3, NodePath, PandaNode, VBase3, Vec3

from . import arenas
from .spatial import make_rigid_transform, required_rotation

_logger: Final = logging.getLogger(__name__)


def make_body(
    *,
    name: str,
    shape: BulletShape,
    mass: float,
    position: VBase3,
    parent: NodePath | None = None,
    world: BulletWorld | None = None,
    collision_mask: CollideMask | int = CollideMask.all_on(),
) -> NodePath[BulletRigidBodyNode]:
    """Return a NodePath for a new rigid body with the given characteristics"""
    node = BulletRigidBodyNode(name)
    node.add_shape(shape)
    node.set_mass(mass)
    if parent is None:
        path = NodePath(node)
    else:
        path = parent.attach_new_node(node)
    path.set_pos(position)
    path.set_collide_mask(CollideMask(collision_mask))
    if world is not None:
        world.attach(node)
    return path


def make_ball_joint(
    node_path_a: NodePath,
    node_path_b: NodePath,
    *,
    position: VBase3,
    rotation: Mat3 = Mat3.ident_mat(),
) -> BulletGenericConstraint:
    a_to_joint = position
    b_to_joint = node_path_b.get_relative_point(node_path_a, position)
    frame_a = make_rigid_transform(rotation, a_to_joint)
    frame_b = make_rigid_transform(rotation, b_to_joint)
    joint = BulletGenericConstraint(
        node_path_a.node(),
        node_path_b.node(),
        frame_a=frame_a,
        frame_b=frame_b,
        use_frame_a=True,
    )
    return joint


def make_hinge_joint(
    node_path_a: NodePath, node_path_b: NodePath, *, position: VBase3, axis: VBase3
) -> BulletHingeConstraint:
    a_to_joint = position
    b_to_joint = node_path_b.get_relative_point(node_path_a, position)
    joint = BulletHingeConstraint(
        node_path_a.node(),
        node_path_b.node(),
        pivot_a=a_to_joint,
        pivot_b=b_to_joint,
        axis_a=axis,
        axis_b=axis,
        use_frame_a=True,
    )
    return joint


def make_slider_joint(
    node_path_a: NodePath, node_path_b: NodePath, *, position: VBase3, axis: VBase3
) -> BulletSliderConstraint:
    a_to_joint = position
    b_to_joint = node_path_b.get_relative_point(node_path_a, position)
    rotation = required_rotation(Vec3.unit_x(), axis)
    frame_a = make_rigid_transform(rotation, a_to_joint)
    frame_b = make_rigid_transform(rotation, b_to_joint)
    joint = BulletSliderConstraint(
        node_path_a.node(),
        node_path_b.node(),
        frame_a=frame_a,
        frame_b=frame_b,
        use_frame_a=True,
    )
    return joint


def make_cone_joint(
    node_path_a: NodePath,
    node_path_b: NodePath,
    *,
    position: VBase3,
    axis: VBase3,
) -> BulletConeTwistConstraint:
    a_to_joint = position
    b_to_joint = node_path_b.get_relative_point(node_path_a, position)
    rotation = required_rotation(Vec3.unit_x(), axis)
    frame_a = make_rigid_transform(rotation, a_to_joint)
    frame_b = make_rigid_transform(rotation, b_to_joint)
    joint = BulletConeTwistConstraint(
        node_path_a.node(), node_path_b.node(), frame_a=frame_a, frame_b=frame_b
    )
    return joint


def required_projectile_velocity(
    delta_position: VBase3,
    speed: float,
    *,
    gravity: VBase3 = Vec3(0, 0, -9.81),
) -> Vec3:
    g_squared = gravity.length_squared()
    d_squared = delta_position.length_squared()
    x = speed * speed + delta_position.dot(gravity)
    try:
        root = math.sqrt(x * x - d_squared * g_squared)
    except ValueError:
        root = 0
    direction = delta_position * g_squared - gravity * (x - root)
    return Vec3(direction.normalized() * speed)


def spawn_projectile(
    *,
    name: str = 'projectile',
    position: VBase3 = Vec3.zero(),
    mass: float = 1,
    velocity: VBase3 = Vec3.zero(),
    arena: arenas.Arena,
    collision_mask: CollideMask | int = CollideMask.all_on(),
) -> NodePath[BulletRigidBodyNode]:
    projectile = make_body(
        name=name,
        shape=BulletSphereShape(0.1),
        mass=mass,
        position=position,
        parent=arena.root,
        world=arena.world,
        collision_mask=collision_mask,
    )

    def impact_callback(node: PandaNode, manifold: BulletPersistentManifold) -> None:
        if any(p.distance < 0.01 for p in manifold.manifold_points):
            arena.world.remove(node)
            projectile.remove_node()

    projectile_node = projectile.node()
    projectile_node.python_tags['impact_callback'] = impact_callback
    projectile_node.linear_velocity = Vec3(velocity)
    return projectile


def make_world(*, gravity: VBase3) -> BulletWorld:
    world = BulletWorld()
    world.set_gravity(gravity)
    return world
