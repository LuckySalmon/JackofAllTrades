from collections.abc import Callable
from typing import Protocol

from panda3d.core import PythonTask as Task

done: int
cont: int
again: int
pickup: int
exit: int

class _owner(Protocol):
    def _addTask(self, task: Task) -> None: ...

    def _clearTask(self, task: Task) -> None: ...

# class Task:
#     done: int
#     cont: int
#     again: int
#     pickup: int
#     exit: int

class TaskManager:
    def add(self, funcOrTask: Task | Callable,
            name: str,
            extraArgs: list | None = None,
            appendTask: bool = False,
            sort: int = 0,
            priority: int = 0,
            uponDeath: Callable[..., None] | None = None,
            taskChain: str | None = None,
            owner: _owner | None = None,
            delay: float = 0) -> Task: ...
