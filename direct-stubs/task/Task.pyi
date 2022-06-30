from collections.abc import Callable, Sequence
from typing import Any, Literal, Protocol

from panda3d.core import AsyncTask, PythonTask as Task

done: Literal[0]
cont: Literal[1]
again: Literal[2]
pickup: Literal[3]
exit: Literal[4]

class _TaskOwner(Protocol):
    def _addTask(self, task: Task) -> None: ...
    def _clearTask(self, task: Task) -> None: ...

class TaskManager:
    def add(self,
            funcOrTask: AsyncTask | Callable,
            name: str | None,
            sort: int | None = None,
            extraArgs: Sequence[Any] | None = None,
            priority: int | None = None,
            appendTask: bool = False,
            uponDeath: Callable[..., object] | None = None,
            taskChain: str | None = None,
            owner: _TaskOwner | None = None,
            delay: float | None = None) -> Task: ...
