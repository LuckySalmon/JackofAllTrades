from ..core import PandaNode, TransformState
from .BulletShape import BulletShape

class BulletBodyNode(PandaNode):
    def addShape(self, shape: BulletShape, xform: TransformState = ...) -> None: ...

    def setActive(self, active: bool, force: bool = False) -> None: ...
