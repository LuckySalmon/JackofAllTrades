from collections.abc import Callable, Iterable

class DirectObject:
    def __init__(self) -> None: ...

    def accept(self,
               event: str,
               method: Callable,
               extraArgs: Iterable = ...) -> None: ...
