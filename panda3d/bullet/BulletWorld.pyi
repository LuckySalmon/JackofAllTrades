from ..core import TypedReferenceCount, TypedObject, LVector3f
from .BulletRigidBodyNode import BulletRigidBodyNode
from .BulletDebugNode import BulletDebugNode
from .BulletConstraint import BulletConstraint

class BulletWorld(TypedReferenceCount):
    def __init__(self) -> None: ...

    def attach(self, object: TypedObject) -> None: ...

    def attachConstraint(self, constraint: BulletConstraint, linked_collision: bool = False) -> None: ...

    def attachRigidBody(self, node: BulletRigidBodyNode) -> None: ...

    def setDebugNode(self, node: BulletDebugNode) -> None: ...

    def setGravity(self, gravity: LVector3f) -> None: ...

    def doPhysics(self, dt: float, max_substeps: int = 1, stepsize: float = 1/60) -> int: ...