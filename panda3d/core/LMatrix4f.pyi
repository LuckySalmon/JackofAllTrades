from .LMatrix3f import LMatrix3f
from .LVecBase3f import LVecBase3f
from .LVecBase4f import LVecBase4f

class LMatrix4f:
    def __init__(self, upper3: LMatrix3f, trans: LVecBase3f) -> None: ...

    def getUpper3(self) -> LMatrix3f: ...

    def xform(self, v: LVecBase4f) -> LVecBase4f: ...
