from panda3d.core import ClockObject
from .ShowBase import ShowBase

globalClock: ClockObject = ClockObject.getGlobalClock()
base: ShowBase  # only exists once an instance of ShowBase is created
