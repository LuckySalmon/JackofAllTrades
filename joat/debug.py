from panda3d.bullet import BulletGenericConstraint
from panda3d.core import GeomNode, LColor, LineSegs, LVecBase3


def show_constraint_axes(
    constraint: BulletGenericConstraint,
    at: LVecBase3 = LVecBase3(),
    *,
    scale: float = 0.25,
) -> GeomNode:
    segments = LineSegs()
    for i in range(3):
        color = LColor()
        color[i] = 1
        segments.set_color(color)
        segments.move_to(at)
        segments.draw_to(at + constraint.get_axis(i) * scale)
    return segments.create()


def draw_path(start: LVecBase3, *path: LVecBase3, color: LColor = LColor()) -> GeomNode:
    segments = LineSegs()
    segments.set_color(color)
    segments.move_to(start)
    for point in path:
        segments.draw_to(point)
    return segments.create()
