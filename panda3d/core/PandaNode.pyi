from .TypedWritableReferenceCount import TypedWritableReferenceCount
from .Namable import Namable
from .TransformState import TransformState
from .Thread import Thread

class PandaNode(TypedWritableReferenceCount, Namable):
    def setTransform(self, transform: TransformState, current_thread: Thread = ...): ...
