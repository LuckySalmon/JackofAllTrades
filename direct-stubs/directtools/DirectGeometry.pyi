from typing import overload, TypeAlias

from panda3d.core import (
    NodePath,
    LVecBase4f,
    LVecBase3f,
    LPoint3f,
    LMatrix3f,
    UnalignedLVecBase4f,
    LMatrix4f,
    GeomNode,
)

_Vec3f: TypeAlias = LVecBase3f | LMatrix3f.Row | LMatrix3f.CRow
_Vec4f: TypeAlias = LVecBase4f | UnalignedLVecBase4f | LMatrix4f.Row | LMatrix4f.CRow

class LineNodePath(NodePath[GeomNode]):
    def __init__(self,
                 parent: NodePath | None = None,
                 name: str | None = None,
                 thickness: float = 1.0,
                 colorVec: _Vec4f = ...) -> None: ...
    @overload
    def moveTo(self, v: _Vec3f) -> None: ...
    @overload
    def moveTo(self, x: float, y: float, z: float) -> None: ...
    @overload
    def drawTo(self, v: _Vec3f) -> None: ...
    @overload
    def drawTo(self, x: float, y: float, z: float) -> None: ...
    def create(self, frameAccurate: bool = False) -> None: ...
    def reset(self) -> None: ...
    @overload
    def setColor(self, color: _Vec4f) -> None: ...
    @overload
    def setColor(self, r: float, g: float, b: float, a: float) -> None: ...
    def getCurrentPosition(self) -> LPoint3f: ...
