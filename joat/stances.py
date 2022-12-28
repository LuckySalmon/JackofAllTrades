from dataclasses import dataclass
from typing import Final

from panda3d.core import Vec3


@dataclass
class Stance:
    left_hand_pos: Vec3
    right_hand_pos: Vec3
    left_arm_angle: float = 0
    right_arm_angle: float = 0


T_POSE: Final = Stance(Vec3(0, +1, 0), Vec3(0, -1, 0))
BOXING_STANCE: Final = Stance(Vec3(0.25, -0.125, 0), Vec3(0.25, +0.125, 0))
