from collections.abc import Sequence
from typing import Any

from panda3d.core.NodePath import NodePath
from .DirectGuiBase import DirectGuiWidget

class DirectFrame(DirectGuiWidget):
    def __init__(self, parent: NodePath | None = None, **kw: Any) -> None: ...
    def destroy(self) -> None: ...
    def setText(self, text: str | Sequence[str] | None = None) -> None: ...
