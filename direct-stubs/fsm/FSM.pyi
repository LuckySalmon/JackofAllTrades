from typing import Any

from ..showbase.DirectObject import DirectObject

class FSM(DirectObject):
    def __init__(self, name: str) -> None: ...

    def request(self, request: str, *args: Any) -> None: ...
