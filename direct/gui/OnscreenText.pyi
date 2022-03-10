from typing import Any, Literal, overload

from panda3d.core import NodePath

Color = tuple[float, float, float, float] | None
OrderedPair = tuple[float, float]

class OnscreenText(NodePath):
    def __init__(self,
                 text: str = '',
                 style: int = 1,
                 pos: OrderedPair = (0, 0),
                 roll: float = 0,
                 scale: float | OrderedPair | None = None,
                 fg: Color = None,
                 bg: Color = None,
                 shadow: Color = None,
                 shadowOffset: OrderedPair = (0.04, 0.04),
                 frame: Color = None,
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

    @overload
    def setTextPos(self, x: float, y: float) -> None: ...

    @overload
    def setTextPos(self, pos: OrderedPair) -> None: ...

    def setText(self, text: str) -> None: ...
