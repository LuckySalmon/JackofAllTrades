from collections.abc import Coroutine
from typing import Any, Final

from panda3d.core import AsyncTask, AsyncTaskManager, PythonTask

TASK_MANAGER: Final = AsyncTaskManager.get_global_ptr()


def add_task(task: AsyncTask | Coroutine[Any, None, object]) -> None:
    if not isinstance(task, AsyncTask):
        task = PythonTask(task)
    TASK_MANAGER.add(task)
