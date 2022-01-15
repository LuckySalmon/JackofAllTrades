from .ReferenceCount import ReferenceCount

class ClockObject(ReferenceCount):
    @staticmethod
    def getGlobalClock() -> ClockObject: ...
