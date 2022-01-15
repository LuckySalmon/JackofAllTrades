from typing import Any
from collections.abc import Sequence

from .DirectGuiBase import DirectGuiWidget

class DirectFrame(DirectGuiWidget):
    def __init__(self, parent: Any = None, **kw: Any) -> None: ...

    def setText(self, text: str | Sequence | None = None): ...

    def destroy(self) -> None: ...
