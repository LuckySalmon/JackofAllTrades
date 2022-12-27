from __future__ import annotations

import logging
import math
from collections.abc import Callable, Iterable
from functools import partial
from typing import Final

from direct.showbase import ShowBaseGlobal
from direct.task.Task import Task
from panda3d.bullet import (
    BulletBoxShape,
    BulletCapsuleShape,
    BulletConeTwistConstraint,
    BulletGenericConstraint,
    BulletHingeConstraint,
    BulletPersistentManifold,
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
    PandaNode,
    Quat,
    TransformState,
    VBase3,
    Vec3,
)

from . import moves

_logger: Final = logging.getLogger(__name__)

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
    world: BulletWorld,
    instant_effects: Iterable[moves.InstantEffect] = (),
    status_effects: Iterable[moves.StatusEffect] = (),
    collision_mask: CollideMask | int = CollideMask.all_on(),
) -> None:
    projectile = make_body(
        name,
        shape='sphere',
        dimensions=[0.1],
        mass=mass,
        position=position,
        parent=ShowBaseGlobal.base.render,
        world=world,
        collision_mask=collision_mask,
    )

    def impact_callback(node: PandaNode, manifold: BulletPersistentManifold) -> None:
        if node == manifold.node0:
            other_node = manifold.node1
        else:
            other_node = manifold.node0
        for point in manifold.manifold_points:
            if point.distance > 0.01:
                continue
            _logger.debug(f'{name} hit {other_node.name}')
            other_fighter = other_node.python_tags.get('fighter')
            if other_fighter is not None:
                _logger.debug(f'{other_fighter} was hit by {name}')
                for effect in instant_effects:
                    effect.apply(other_fighter)
                other_fighter.copy_effects(status_effects)
            world.remove(node)
            projectile.remove_node()
            break

    projectile_node = projectile.node()
    projectile_node.python_tags['impact_callback'] = impact_callback
    projectile_node.linear_velocity = Vec3(velocity)


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
