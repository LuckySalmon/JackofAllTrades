from __future__ import annotations

from dataclasses import dataclass, field

from direct.showbase import ShowBaseGlobal
from direct.showbase.DirectObject import DirectObject
from panda3d import bullet
from panda3d.core import AsyncTask

from .characters import Fighter


@dataclass
class Arena:
    fighter_1: Fighter
    fighter_2: Fighter
    world: bullet.BulletWorld = field(kw_only=True)

    def __post_init__(self) -> None:
        debug_node = bullet.BulletDebugNode('Bullet Debug Node')
        debug_node.show_constraints(False)
        self.world.set_debug_node(debug_node)
        debug_node_path = ShowBaseGlobal.base.render.attach_new_node(debug_node)
        debug_node_path.show()

        def toggle_debug() -> None:
            if debug_node_path.is_hidden():
                debug_node_path.show()
            else:
                debug_node_path.hide()

        DirectObject().accept('f1', toggle_debug)

    def get_fighter(self, index: int) -> Fighter:
        if index == 0:
            return self.fighter_1
        elif index == 1:
            return self.fighter_2
        else:
            raise IndexError(f'{self} has no fighter at index {index}')

    def update(self, task: AsyncTask) -> int:
        self.handle_collisions()
        self.world.do_physics(ShowBaseGlobal.globalClock.dt)
        return task.DS_cont

    def handle_collisions(self) -> None:
        for manifold in self.world.manifolds:
            if not manifold.node0.into_collide_mask & manifold.node1.into_collide_mask:
                continue
            for node in (manifold.node0, manifold.node1):
                impact_callback = node.python_tags.get('impact_callback')
                if impact_callback is not None:
                    impact_callback(node, manifold)
