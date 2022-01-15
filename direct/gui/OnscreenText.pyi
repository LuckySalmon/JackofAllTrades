from panda3d.core import NodePath

from typing import Any
from typing import Literal
from typing import Optional

Alignment = Literal[0, 1, 2]
Direction = Literal['ltr', 'rtl']
Color = tuple[float, float, float, float]
OrderedPair = tuple[float, float]
Scale = float | OrderedPair

class OnscreenText(NodePath):
    def __init__(self,
                 text: str = '',
                 style: int = 1,
                 pos: OrderedPair = (0, 0),
                 roll: float = 0,
                 scale: Optional[Scale] = None,
                 fg: Optional[Color] = None,
                 bg: Optional[Color] = None,
                 shadow: Optional[Color] = None,
                 shadowOffset: OrderedPair = (0.04, 0.04),
                 frame: Optional[Color] = None,
                 align: Optional[Alignment] = None,
                 wordwrap: Optional[int] = None,
                 drawOrder: Optional[int] = None,
                 decal: bool = False,
                 font: Any = None,
                 parent: Optional[NodePath] = None,
                 sort: int = 0,
                 mayChange: bool = True,
                 direction: Optional[Direction] = None) -> None: ...

    def setTextPos(self, x: float, y: float | None = None) -> None: ...

    def setText(self, text: str) -> None: ...
