from __future__ import annotations

from dataclasses import dataclass, field
from typing_extensions import Never

from direct.showbase.DirectObject import DirectObject
from panda3d import bullet
from panda3d.core import AsyncTaskPause, ClockObject, NodePath, Vec3

from .characters import Fighter


@dataclass
class Arena:
    fighter_1: Fighter
    fighter_2: Fighter
    world: bullet.BulletWorld = field(kw_only=True)
    root: NodePath = field(kw_only=True)

    def __post_init__(self) -> None:
        ground_node = bullet.BulletRigidBodyNode('Ground')
        ground_node.add_shape(bullet.BulletPlaneShape(Vec3(0, 0, 1), 1))
        ground_node_path = self.root.attach_new_node(ground_node)
        ground_node_path.set_pos(0, 0, -2)
        self.world.attach(ground_node)

        self.fighter_1.enter_arena(self)
        self.fighter_2.enter_arena(self)

        debug_node = bullet.BulletDebugNode('Bullet Debug Node')
        debug_node.show_constraints(False)
        self.world.set_debug_node(debug_node)
        debug_node_path = self.root.attach_new_node(debug_node)
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

    async def update(self) -> Never:
        clock = ClockObject.get_global_clock()
        prev_time = clock.frame_time
        while True:
            now = clock.frame_time
            self.handle_collisions()
            self.world.do_physics(now - prev_time)
            prev_time = now
            await AsyncTaskPause(0)

    def handle_collisions(self) -> None:
        for manifold in self.world.manifolds:
            if not manifold.node0.into_collide_mask & manifold.node1.into_collide_mask:
                continue
            for node in (manifold.node0, manifold.node1):
                impact_callback = node.python_tags.get('impact_callback')
                if impact_callback is not None:
                    impact_callback(node, manifold)
