from ..core import LVector3f
from ..core import TransformState
from .BulletConstraint import BulletConstraint
from .BulletRigidBodyNode import BulletRigidBodyNode
from .BulletRotationalLimitMotor import BulletRotationalLimitMotor

class BulletGenericConstraint(BulletConstraint):
    def __init__(self,
                 node_a: BulletRigidBodyNode,
                 node_b: BulletRigidBodyNode,
                 frame_a: TransformState,
                 frame_b: TransformState,
                 use_frame_a: bool) -> None: ...

    def setAngularLimit(self, axis: int, low: float, high: float) -> None: ...

    def getAngle(self, axis: int) -> float: ...

    def getRotationalLimitMotor(self, axis: int) -> BulletRotationalLimitMotor: ...

    def getAxis(self, axis: int) -> LVector3f: ...
