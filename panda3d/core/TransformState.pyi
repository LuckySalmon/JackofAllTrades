from .NodeCachedReferenceCount import NodeCachedReferenceCount
from .LMatrix4f import LMatrix4f
from .LVecBase3f import LVecBase3f
from .LPoint3f import LPoint3f

class TransformState(NodeCachedReferenceCount):
    @classmethod
    def makeMat(cls, mat: LMatrix4f) -> TransformState: ...

    @classmethod
    def makePosHpr(cls, pos: LVecBase3f, hpr: LVecBase3f) -> TransformState: ...

    def getPos(self) -> LPoint3f: ...

    def getMat(self) -> LMatrix4f: ...
