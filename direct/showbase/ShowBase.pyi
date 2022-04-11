from panda3d.core import NodePath
from ..task.Task import TaskManager
from .DirectObject import DirectObject

class ShowBase(DirectObject):
    def __init__(self, fStartDirect: bool = True, windowType: str | None = None) -> None: ...

    @property
    def render(self) -> NodePath: ...

    @property
    def cam(self) -> NodePath: ...

    @property
    def taskMgr(self) -> TaskManager: ...

    def run(self) -> None: ...

    def userExit(self) -> None: ...

