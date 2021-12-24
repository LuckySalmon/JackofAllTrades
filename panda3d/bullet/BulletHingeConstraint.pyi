from ..core import LPoint3f, LVector3f
from .BulletConstraint import BulletConstraint
from .BulletRigidBodyNode import BulletRigidBodyNode

class BulletHingeConstraint(BulletConstraint):
    def __init__(self,
                 node_a: BulletRigidBodyNode,
                 node_b: BulletRigidBodyNode,
                 pivot_a: LPoint3f,
                 pivot_b: LPoint3f,
                 axis_a: LVector3f,
                 axis_b: LVector3f,
                 use_frame_a: bool) -> None: ...

    def setLimit(self,
                 low: float,
                 high: float,
                 softness: float = 0.9,
                 bias: float = 0.3,
                 relaxation: float = 1.0) -> None: ...

    def setMaxMotorImpulse(self, max_impulse: float) -> None: ...

    def enableMotor(self, enable: bool) -> None: ...

    def setMotorTarget(self, target_angle: float, dt: float) -> None: ...
