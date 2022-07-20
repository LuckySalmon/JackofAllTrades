from typing import Any, Literal, overload, TypeAlias

from panda3d.core import NodePath, TextNode

_Color: TypeAlias = tuple[float, float, float, float] | None
_OrderedPair: TypeAlias = tuple[float, float]

class OnscreenText(NodePath[TextNode]):
    def __init__(self,
                 text: str = '',
                 style: int = 1,
                 pos: _OrderedPair = (0, 0),
                 roll: float = 0,
                 scale: float | _OrderedPair | None = None,
                 fg: _Color = None,
                 bg: _Color = None,
                 shadow: _Color = None,
                 shadowOffset: _OrderedPair = (0.04, 0.04),
                 frame: _Color = None,
                 align: Literal[0, 1, 2, None] = None,
                 wordwrap: int | None = None,
                 drawOrder: int | None = None,
                 decal: bool = False,
                 font: Any = None,
                 parent: NodePath | None = None,
                 sort: int = 0,
                 mayChange: bool = True,
                 direction: Literal['ltr', 'rtl', None] = None) -> None: ...
    def __setitem__(self, key: str, value: Any) -> None: ...
    def setText(self, text: str) -> None: ...
    @overload
    def setTextPos(self, x: float, y: float) -> None: ...
    @overload
    def setTextPos(self, x: _OrderedPair) -> None: ...
