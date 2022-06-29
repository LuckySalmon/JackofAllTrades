from typing import Literal
from panda3d.core import PandaNode, TextEncoder

class TextProperties:
    A_left: Literal[0]
    A_right: Literal[1]
    A_center: Literal[2]
    ALeft = A_left
    ARight = A_right
    ACenter = A_center

class TextNode(PandaNode, TextEncoder, TextProperties):
    ...
