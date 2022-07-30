from panda3d.core import ClockObject
from .ShowBase import ShowBase

globalClock: ClockObject = ClockObject.get_global_clock()
base: ShowBase  # only exists once an instance of ShowBase is created
