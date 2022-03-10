class Messenger:
    def send(self,
             event: str,
             sentArgs: list = ...,
             taskChain: str | None = None) -> None: ...
