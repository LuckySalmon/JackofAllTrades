from typing import overload

from panda3d.core import NodePath, LVecBase4f, LVecBase3f, LPoint3f

class LineNodePath(NodePath):
    def __init__(self,
                 parent: NodePath | None = None,
                 name: str | None = None,
                 thickness: float = 1.0,
                 colorVec: LVecBase4f = LVecBase4f(1)) -> None: ...

    @overload
    def moveTo(self, v: LVecBase3f) -> None: ...

    @overload
    def moveTo(self, x: float, y: float, z: float) -> None: ...

    @overload
    def drawTo(self, v: LVecBase3f) -> None: ...

    @overload
    def drawTo(self, x: float, y: float, z: float) -> None: ...

    def create(self, frameAccurate: bool = False) -> None: ...

    def reset(self) -> None: ...

    @overload
    def setColor(self, color: LVecBase4f) -> None: ...

    @overload
    def setColor(self, r: float, g: float, b: float, a: float) -> None: ...

    def getCurrentPosition(self) -> LPoint3f: ...
