from collections.abc import Sequence
from typing import Any

class Messenger:
    def send(self,
             event: str,
             sentArgs: Sequence[Any] = ...,
             taskChain: str | None = None) -> None: ...
