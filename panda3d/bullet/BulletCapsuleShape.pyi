from .BulletShape import BulletShape

from typing import Literal

BulletUpAxis = Literal[0, 1, 2]

class BulletCapsuleShape(BulletShape):
    def __init__(self, radius: float, height: float, up: BulletUpAxis) -> None: ...
