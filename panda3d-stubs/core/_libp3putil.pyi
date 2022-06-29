from panda3d.core import ReferenceCount, Thread

class ClockObject(ReferenceCount):
    def get_dt(self, current_thread: Thread = ...) -> float: ...
    @staticmethod
    def get_global_clock() -> ClockObject: ...
    getDt = get_dt
    getGlobalClock = get_global_clock
