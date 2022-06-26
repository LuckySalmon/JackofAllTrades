import math
from collections.abc import Iterable

from panda3d.bullet import (
    BulletPlaneShape,
    BulletRigidBodyNode,
    BulletSphereShape,
    BulletBoxShape,
    BulletCapsuleShape,
    BulletWorld,
    BulletGenericConstraint,
    BulletHingeConstraint,
    BulletConeTwistConstraint,
)
from panda3d.core import (
    NodePath,
    VBase3,
    Vec3,
    Point3,
    Quat,
    Mat3,
    Mat4,
    TransformState,
)
from direct.showbase import ShowBaseGlobal
from direct.task.Task import Task


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
              dimensions: Iterable[float],
              mass: float,
              position: VBase3 | Iterable[float],
              parent: NodePath,
              world: BulletWorld) -> 'NodePath[BulletRigidBodyNode]':
    """Return a NodePath for a new rigid body with the given characteristics"""
    constructor = shape_constructors[shape]
    node = BulletRigidBodyNode(name)
    node.addShape(constructor(*dimensions))
    node.setMass(mass)
    path = parent.attachNewNode(node)
    path.setPos(*position)
    world.attach(node)
    return path


def make_ball_joint(position: VBase3,
                    node_path_a: NodePath,
                    node_path_b: NodePath,
                    rotation: Mat3) -> BulletGenericConstraint:
    a_to_joint = position
    b_to_joint = node_path_b.getRelativePoint(node_path_a, position)
    frame_a = make_rigid_transform(rotation, a_to_joint)
    frame_b = make_rigid_transform(rotation, b_to_joint)
    joint = BulletGenericConstraint(node_path_a.node(), node_path_b.node(),
                                    frame_a, frame_b, True)
    return joint


def make_hinge_joint(position: VBase3,
                     node_path_a: NodePath,
                     node_path_b: NodePath,
                     axis: Vec3) -> BulletHingeConstraint:
    a_to_joint = Point3(position)
    b_to_joint = node_path_b.getRelativePoint(node_path_a, position)
    joint = BulletHingeConstraint(node_path_a.node(), node_path_b.node(),
                                  a_to_joint, b_to_joint, axis, axis, True)
    return joint


def make_cone_joint(position: VBase3,
                    node_path_a: NodePath,
                    node_path_b: NodePath,
                    hpr: VBase3) -> BulletConeTwistConstraint:
    a_to_joint = position
    b_to_joint = node_path_b.getRelativePoint(node_path_a, position)
    frame_a = TransformState.makePosHpr(a_to_joint, hpr)
    frame_b = TransformState.makePosHpr(b_to_joint, node_path_b.getRelativeVector(node_path_a, hpr))
    joint = BulletConeTwistConstraint(node_path_a.node(), node_path_b.node(),
                                      frame_a, frame_b)
    return joint


def make_world(gravity: float) -> BulletWorld:
    world = BulletWorld()
    world.setGravity(Vec3(0, 0, -gravity))

    ground = ShowBaseGlobal.base.render.attachNewNode(BulletRigidBodyNode('Ground'))
    ground.node().addShape(BulletPlaneShape(Vec3(0, 0, 1), 1))
    ground.setPos(0, 0, -2)
    world.attach(ground.node())

    return world


def update_physics(world: BulletWorld, task: Task) -> int:
    dt = ShowBaseGlobal.globalClock.getDt()
    world.doPhysics(dt)
    return task.cont
