from typing import overload

from .LVecBase3f import LVecBase3f

class LVector3f(LVecBase3f):
    @overload
    def __init__(self, copy: LVecBase3f) -> None: ...

    @overload
    def __init__(self, x: float, y: float, z: float) ->  None: ...
