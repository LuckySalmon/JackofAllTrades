from ..core import TypedReferenceCount

class BulletConstraint(TypedReferenceCount):
    def setDebugDrawSize(self, size: float) -> None: ...
