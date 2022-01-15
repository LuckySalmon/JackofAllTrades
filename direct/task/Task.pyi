from typing import Callable

from panda3d.core import PythonTask

Task = PythonTask
done: int
cont: int
again: int
pickup: int
exit: int

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
            uponDeath: Callable = None,
            taskChain: str | None = None,
            owner: {object | None} = None,
            delay: float = 0) -> Task: ...
