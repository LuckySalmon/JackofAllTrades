from ..core.LVector3f import LVector3f
from .BulletShape import BulletShape

class BulletPlaneShape(BulletShape):
    def __init__(self, normal: LVector3f, constant: float) -> None: ...
