from .LVecBase4f import LVecBase4f

class LQuaternionf(LVecBase4f):
    def __init__(self, r: float, i: float, j: float, k: float) -> None: ...

    def normalize(self) -> bool: ...