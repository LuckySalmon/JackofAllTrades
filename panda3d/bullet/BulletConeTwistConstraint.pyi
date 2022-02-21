from ..core import TransformState
from .BulletConstraint import BulletConstraint
from .BulletRigidBodyNode import BulletRigidBodyNode

class BulletConeTwistConstraint(BulletConstraint):
    def __init__(self,
                 node_a: BulletRigidBodyNode,
                 node_b: BulletRigidBodyNode,
                 frame_a: TransformState,
                 frame_b: TransformState) -> None: ...
