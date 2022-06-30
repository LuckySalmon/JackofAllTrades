from typing import Literal

from panda3d.core import NodePath
from ..task.Task import TaskManager
from .DirectObject import DirectObject

class ShowBase(DirectObject):
    render: NodePath
    cam: NodePath
    taskMgr: TaskManager
    def __init__(self,
                 fStartDirect: bool = True,
                 windowType: Literal['onscreen', 'offscreen', 'none', None] = None) -> None: ...
    def userExit(self) -> None: ...
    def run(self) -> None: ...
