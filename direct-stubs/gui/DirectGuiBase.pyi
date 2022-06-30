from typing import Any

from panda3d.core import NodePath
from ..showbase.DirectObject import DirectObject

class DirectGuiBase(DirectObject):
    def __setitem__(self, key: str, value: Any) -> None: ...

    def __getitem__(self, option: str) -> Any: ...

class DirectGuiWidget(DirectGuiBase, NodePath): ...
