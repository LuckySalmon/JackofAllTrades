from typing import overload

from .LVecBase3f import LVecBase3f

class LVecBase4f:
    @overload
    def __init__(self, x: float, y: float, z: float, w: float) -> None: ...

    @overload
    def __init__(self, copy: LVecBase3f, w: float) -> None: ...

    @overload
    def __init__(self, fill_value: float) -> None: ...

    def getXyz(self) -> LVecBase3f: ...
