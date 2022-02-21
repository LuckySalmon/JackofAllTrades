import math
from collections.abc import Sequence

from panda3d.bullet import (
    BulletPlaneShape,
    BulletRigidBodyNode,
    BulletSphereShape,
    BulletBoxShape,
    BulletCapsuleShape,
    BulletWorld
)
from panda3d.core import (
    NodePath,
    VBase3,
    Vec3,
    Quat,
    Mat3,
    Mat4,
    TransformState,
)
from direct.showbase.ShowBaseGlobal import globalClock


shape_constructors = dict(sphere=BulletSphereShape,
                          box=lambda *args: BulletBoxShape(Vec3(*args)),
                          capsule_x=lambda *args: BulletCapsuleShape(*args, 0),
                          capsule_y=lambda *args: BulletCapsuleShape(*args, 1),
                          capsule_z=lambda *args: BulletCapsuleShape(*args, 2))


def make_quaternion(angle: float, axis: VBase3) -> Quat:
    """Return a quaternion with the given characteristics"""
    radians = angle/360 * math.pi
    cosine = math.cos(radians/2)
    quaternion = Quat(cosine, *axis)
    quaternion.normalize()
    return quaternion


def make_rigid_transform(rotation: Mat3, translation: VBase3) -> TransformState:
    """Return a TransformState comprising the given rotation followed by the given translation"""
    return TransformState.makeMat(Mat4(rotation, translation))


def make_body(name: str,
              shape: str,
              dimensions: Sequence[float],
              mass: float,
              position: VBase3 | Sequence[float],
              parent: NodePath,
              world: BulletWorld) -> 'NodePath[BulletRigidBodyNode]':
    """Return a NodePath for a new rigid body with the given characteristics"""
    constructor = shape_constructors[shape]
    node = BulletRigidBodyNode(name)
    shape = constructor(*dimensions)
    node.addShape(shape)
    node.setMass(mass)
    path = parent.attachNewNode(node)
    path.setPos(*position)
    world.attachRigidBody(node)
    return path


def make_world(gravity: float, render: NodePath) -> BulletWorld:
    world = BulletWorld()
    world.setGravity(Vec3(0, 0, -gravity))

    ground = render.attachNewNode(BulletRigidBodyNode('Ground'))
    ground.node().addShape(BulletPlaneShape(Vec3(0, 0, 1), 1))
    ground.setPos(0, 0, -2)
    world.attachRigidBody(ground.node())

    return world


def update_physics(world: BulletWorld, task) -> int:
    dt = globalClock.getDt()
    world.doPhysics(dt)
    return task.cont
