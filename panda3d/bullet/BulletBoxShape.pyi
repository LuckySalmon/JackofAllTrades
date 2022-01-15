from ..core import LVecBase3f
from .BulletShape import BulletShape

class BulletBoxShape(BulletShape):
    def __init__(self, halfExtents: LVecBase3f) -> None: ...
