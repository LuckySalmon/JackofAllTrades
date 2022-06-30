from collections.abc import Callable, Iterable
from typing import Any

class DirectObject:
    def __init__(self) -> None: ...
    def accept(self,
               event: str,
               method: Callable[..., Any],
               extraArgs: Iterable[Any] = ...) -> None: ...
