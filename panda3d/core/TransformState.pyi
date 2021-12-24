from .NodeCachedReferenceCount import NodeCachedReferenceCount
from .LMatrix4f import LMatrix4f
from .LVecBase3f import LVecBase3f

class TransformState(NodeCachedReferenceCount):
    @staticmethod
    def makeMat(mat: LMatrix4f) -> TransformState: ...

    @staticmethod
    def makePosHpr(pos: LVecBase3f, hpr: LVecBase3f) -> TransformState: ...
