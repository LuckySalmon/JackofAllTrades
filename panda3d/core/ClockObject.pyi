from .ReferenceCount import ReferenceCount
from .Thread import Thread

class ClockObject(ReferenceCount):
    @staticmethod
    def getGlobalClock() -> ClockObject: ...

    def getDt(current_thread: Thread = ...) -> float: ...
