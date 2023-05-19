from __future__ import annotations

from dataclasses import dataclass, field

from panda3d import bullet
from panda3d.core import AsyncTaskPause, ClockObject, LPoint3, NodePath, Vec3

from .characters import Fighter
from .debug import DebugHandler


@dataclass
class Arena:
    fighter_1: Fighter
    fighter_2: Fighter
    world: bullet.BulletWorld = field(kw_only=True)
    root: NodePath = field(kw_only=True)
    ground: NodePath[bullet.BulletRigidBodyNode] = field(init=False)
    running: bool = field(default=False, init=False)
    debug_handler: DebugHandler = field(init=False)

    def __post_init__(self) -> None:
        ground_node = bullet.BulletRigidBodyNode('Ground')
        ground_node.add_shape(bullet.BulletPlaneShape(Vec3(0, 0, 1), 0))
        self.ground = self.root.attach_new_node(ground_node)
        self.ground.set_pos(0, 0, 0)
        self.world.attach(ground_node)

        if self.fighter_1.name == self.fighter_2.name:
            self.fighter_1.name += ' (1)'
            self.fighter_2.name += ' (2)'
        self.fighter_1.enter_arena(self)
        self.fighter_2.enter_arena(self)

        self.debug_handler = DebugHandler.for_arena(self)

    def get_fighter(self, index: int) -> Fighter:
        if index == 0:
            return self.fighter_1
        elif index == 1:
            return self.fighter_2
        else:
            raise IndexError(f'{self} has no fighter at index {index}')

    async def update(self) -> None:
        self.running = True
        clock = ClockObject.get_global_clock()
        prev_time = clock.frame_time
        while self.running:
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

    def get_mouse_ray(self) -> bullet.BulletClosestHitRayResult:
        from direct.showbase.ShowBaseGlobal import base

        mouse_pos = base.mouseWatcherNode.get_mouse()
        camera = base.cam
        lens = camera.node().get_lens()
        near_point, far_point = LPoint3(), LPoint3()
        lens.extrude(mouse_pos, near_point, far_point)
        origin = self.root.get_relative_point(camera, near_point)
        endpoint = self.root.get_relative_point(camera, far_point)
        return self.world.ray_test_closest(origin, endpoint)

    def exit(self):
        self.running = False
        self.root.detach_node()
        self.fighter_1.exit_arena()
        self.fighter_2.exit_arena()
        self.debug_handler.destroy()
        self.world.remove(self.ground.node())
