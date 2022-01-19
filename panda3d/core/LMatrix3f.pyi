from .LVecBase3f import LVecBase3f

from typing import overload

class LMatrix3f:
    @overload
    def __init__(self,
                 param0: LVecBase3f,
                 param1: LVecBase3f,
                 param2: LVecBase3f) -> None: ...

    @overload
    def __init__(self,
                 param0: float, param1: float, param2: float,
                 param3: float, param4: float, param5: float,
                 param6: float, param7: float, param8: float) -> None: ...

    @staticmethod
    def identMat() -> LMatrix3f: ...

    def xform(self, v: LVecBase3f) -> LVecBase3f: ...
