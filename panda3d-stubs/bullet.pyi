from typing import Literal, TypeAlias, overload
from panda3d.core import (
    PandaNode,
    TransformState,
    TypedObject,
    TypedReferenceCount,
    TypedWritableReferenceCount,
    LVecBase3f,
    LVector3f,
    LMatrix3f,
)

_BulletUpAxis: TypeAlias = Literal[0, 1, 2]
_Vec3f: TypeAlias = LVecBase3f | LMatrix3f.Row | LMatrix3f.CRow

class BulletShape(TypedWritableReferenceCount):
    ...

class BulletBodyNode(PandaNode):
    def add_shape(self, shape: BulletShape, xform: TransformState = ...) -> None: ...
    def set_active(self, active: bool, force: bool = False) -> None: ...
    addShape = add_shape
    setActive = set_active

class BulletBoxShape(BulletShape):
    def __init__(self, halfExtents: _Vec3f) -> None: ...

class BulletCapsuleShape(BulletShape):
    def __init__(self, radius: float, height: float, up: _BulletUpAxis) -> None: ...

class BulletConstraint(TypedReferenceCount):
    def set_debug_draw_size(self, size: float) -> None: ...
    setDebugDrawSize = set_debug_draw_size

class BulletRigidBodyNode(BulletBodyNode):
    def __init__(self, name: str = 'rigid') -> None: ...
    def set_mass(self, mass: float) -> None: ...
    setMass = set_mass

class BulletConeTwistConstraint(BulletConstraint):
    def __init__(self,
                 node_a: BulletRigidBodyNode,
                 node_b: BulletRigidBodyNode,
                 frame_a: TransformState,
                 frame_b: TransformState) -> None: ...

class BulletManifoldPoint:
    @property
    def distance(self) -> float: ...

class BulletContact:
    def get_manifold_point(self) -> BulletManifoldPoint: ...
    getManifoldPoint = get_manifold_point

class BulletContactResult:
    def get_contacts(self) -> tuple[BulletContact, ...]: ...
    getContacts = get_contacts

class BulletDebugNode(PandaNode):
    def __init__(self, name: str = 'debug'): ...
    def show_wireframe(self, show: bool) -> None: ...
    def show_constraints(self, show: bool) -> None: ...
    def show_bounding_boxes(self, show: bool) -> None: ...
    def show_normals(self, show: bool) -> None: ...
    showWireframe = show_wireframe
    showConstraints = show_constraints
    showBoundingBoxes = show_bounding_boxes
    showNormals = show_normals

class BulletWorld(TypedReferenceCount):
    def __init__(self) -> None: ...
    @overload
    def set_gravity(self, gravity: _Vec3f) -> None: ...
    @overload
    def set_gravity(self, gx: float, gy: float, gz: float) -> None: ...
    def do_physics(self, dt: float, max_substeps: int = 1, stepsize: float = 1/60) -> int: ...
    def set_debug_node(self, node: BulletDebugNode) -> None: ...
    def attach(self, object: TypedObject) -> None: ...
    def attach_rigid_body(self, node: BulletRigidBodyNode) -> None: ...
    def attach_constraint(self, constraint: BulletConstraint, linked_collision: bool = False) -> None: ...
    def contact_test_pair(self, node0: PandaNode, node1: PandaNode) -> BulletContactResult: ...
    setGravity = set_gravity
    doPhysics = do_physics
    setDebugNode = set_debug_node
    attachRigidBody = attach_rigid_body
    attachConstraint = attach_constraint
    contactTestPair = contact_test_pair

class BulletRotationalLimitMotor:
    def set_motor_enabled(self, enable: bool) -> None: ...
    def set_max_motor_force(self, force: float) -> None: ...
    def set_target_velocity(self, velocity: float) -> None: ...
    setMotorEnabled = set_motor_enabled
    setMaxMotorForce = set_max_motor_force
    setTargetVelocity = set_target_velocity

class BulletGenericConstraint(BulletConstraint):
    def __init__(self,
                 node_a: BulletRigidBodyNode,
                 node_b: BulletRigidBodyNode,
                 frame_a: TransformState,
                 frame_b: TransformState,
                 use_frame_a: bool) -> None: ...
    def get_axis(self, axis: int) -> LVector3f: ...
    def get_angle(self, axis: int) -> float: ...
    def set_angular_limit(self, axis: int, low: float, high: float) -> None: ...
    def get_rotational_limit_motor(self, axis: int) -> BulletRotationalLimitMotor: ...
    def get_frame_a(self) -> TransformState: ...
    def get_frame_b(self) -> TransformState: ...
    getAxis = get_axis
    getAngle = get_angle
    setAngularLimit = set_angular_limit
    getRotationalLimitMotor = get_rotational_limit_motor
    getFrameA = get_frame_a
    getFrameB = get_frame_b

class BulletHingeConstraint(BulletConstraint):
    def __init__(self,
                 node_a: BulletRigidBodyNode,
                 node_b: BulletRigidBodyNode,
                 pivot_a: _Vec3f,
                 pivot_b: _Vec3f,
                 axis_a: _Vec3f,
                 axis_b: _Vec3f,
                 use_frame_a: bool = ...) -> None: ...
    def set_limit(self,
                  low: float,
                  high: float,
                  softness: float = 0.9,
                  bias: float = 0.3,
                  relaxation: float = 1.0) -> None: ...
    def enable_motor(self, enable: bool) -> None: ...
    def set_max_motor_impulse(self, max_impulse: float) -> None: ...
    def set_motor_target(self, target_angle: float, dt: float) -> None: ...
    setLimit = set_limit
    enableMotor = enable_motor
    setMaxMotorImpulse = set_max_motor_impulse
    setMotorTarget = set_motor_target

class BulletPlaneShape(BulletShape):
    def __init__(self, normal: _Vec3f, constant: float) -> None: ...

class BulletSphereShape(BulletShape):
    def __init__(self, radius: float) -> None: ...
