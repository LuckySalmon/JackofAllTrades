from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing_extensions import Self

from direct.showbase.DirectObject import DirectObject
from panda3d.bullet import BulletDebugNode, BulletGenericConstraint
from panda3d.core import GeomNode, LColor, LineSegs, LVecBase3, NodePath

from . import arenas


@dataclass
class DebugHandler:
    node_path: NodePath[BulletDebugNode]
    acceptor: DirectObject = field(default_factory=DirectObject)
    event: InitVar[str] = 'f1'

    def __post_init__(self, event: str):
        self.acceptor.accept(event, self.toggle_debug)

    @classmethod
    def for_arena(cls, arena: arenas.Arena, event: str = 'f1') -> Self:
        node = BulletDebugNode('Bullet Debug Node')
        node.show_constraints(False)
        arena.world.set_debug_node(node)
        node_path = arena.root.attach_new_node(node)
        node_path.show()
        return cls(node_path, event=event)

    def toggle_debug(self) -> None:
        if self.node_path.is_hidden():
            self.node_path.show()
        else:
            self.node_path.hide()

    def destroy(self) -> None:
        self.node_path.remove_node()
        self.acceptor.ignore_all()


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
