from __future__ import annotations

import enum
import logging
from collections.abc import Container
from typing import Any, Final

import attrs
from panda3d.core import AsyncTaskPause, CollideMask, EventHandler

from . import physics
from .characters import Action, Fighter
from .effects import Effect, EffectBundle, make_effect
from .skeletons import Side

_logger: Final = logging.getLogger(__name__)


class Target(enum.Enum):
    SELF = 'self'
    OTHER = 'opponent'


class MoveType(enum.Enum):
    MELEE = 'melee'
    RANGED = 'ranged'
    INSTANT = 'instant'
    REPOSITIONING = 'repositioning'


@attrs.define
class InstantMove:
    name: str
    effect: Effect | None = None
    valid_targets: Container[Target] = frozenset()

    async def use(self, user: Fighter, using_on: Fighter) -> None:
        if self.effect is not None:
            self.effect.apply(using_on)


@attrs.define(kw_only=True)
class MeleeMove:
    name: str
    accuracy: int = 100
    effect: Effect | None = None
    side: Side = Side.RIGHT
    valid_targets: Container[Target] = frozenset()
    target_part: str = 'torso'

    async def use(self, user: Fighter, using_on: Fighter) -> None:
        target_part = using_on.skeleton.parts[self.target_part]
        target = user.get_position_of(target_part, (1 - self.accuracy / 100))
        arm = user.skeleton.get_arm(self.side)
        fist = arm.forearm.node()
        fist.python_tags['one_shot_effect'] = self.effect
        arm.set_target(target - arm.origin)
        await AsyncTaskPause(1 / (1 + user.speed))
        user.skeleton.assume_stance()
        fist.python_tags.pop('one_shot_effect', None)


@attrs.define
class RangedMove:
    name: str
    accuracy: int = 100
    effect: Effect | None = None
    side: Side | None = None
    valid_targets: Container[Target] = frozenset()
    target_part: str = 'torso'

    async def use(self, user: Fighter, using_on: Fighter) -> None:
        target_part = using_on.skeleton.parts[self.target_part]
        target = user.get_position_of(target_part, (1 - self.accuracy / 100))
        assert user.arena is not None
        root = user.arena.root
        if self.side is None:
            using_part = user.skeleton.parts['head']
            from_position = using_part.get_pos(root)
        else:
            arm = user.skeleton.get_arm(self.side)
            using_part = arm.forearm
            from_position = root.get_relative_point(using_part, (0, -0.25, 0))
            arm.set_target(target - arm.origin)
            await AsyncTaskPause(1 / (1 + user.speed) / 8)
            user.skeleton.assume_stance()
        global_target_position = root.get_relative_point(user.skeleton.core, target)
        projectile = physics.spawn_projectile(
            name=self.name,
            arena=user.arena,
            position=from_position,
            velocity=physics.required_projectile_velocity(
                global_target_position - from_position,
                user.strength * 4,
            ),
            collision_mask=~using_part.get_collide_mask(),
        )
        projectile.node().python_tags.update(one_shot_effect=self.effect, min_impulse=1)
        await AsyncTaskPause(0.2 / user.strength)
        if not projectile.is_empty():
            projectile.set_collide_mask(CollideMask.all_on())


@attrs.define
class RepositioningMove:
    name: str
    valid_targets: Container[Target]

    async def use(self, user: Fighter, using_on: object) -> None:
        assert user.arena is not None
        ring_path = user.project_ring()
        while True:
            await EventHandler.get_global_event_handler().get_future('mouse1')
            result = user.arena.get_mouse_ray()
            if result.node == user.arena.ground.node():
                target = result.hit_pos.xy
                break
        displacement = target - user.skeleton.core.get_pos().xy
        if displacement.length_squared() > user.speed**2:
            target -= displacement
            displacement.normalize()
            displacement *= user.speed
            target += displacement
        ring_path.remove_node()
        await user.skeleton.slide_to(target)


def make_move_from_json(data: dict[str, Any]) -> Action:
    name = data.pop('name').title()
    target = data.pop('target')
    valid_targets = set[Target]()
    if target in ('self', 'any'):
        valid_targets.add(Target.SELF)
    if target in ('other', 'any'):
        valid_targets.add(Target.OTHER)
    effect_params = data.pop('effects', None)
    if effect_params is None:
        effect = None
    else:
        effect = EffectBundle([make_effect(**params) for params in effect_params])
    move_type = MoveType[data.pop('type').upper()]
    side_string = data.pop('side', None)
    side = None if side_string is None else Side[side_string.upper()]
    if move_type is MoveType.MELEE:
        return MeleeMove(
            name=name,
            effect=effect,
            side=side or Side.RIGHT,
            valid_targets=valid_targets,
            **data,
        )
    elif move_type is MoveType.RANGED:
        return RangedMove(
            name=name, effect=effect, side=side, valid_targets=valid_targets, **data
        )
    elif move_type is MoveType.REPOSITIONING:
        return RepositioningMove(name, valid_targets)
    else:
        return InstantMove(name, effect, valid_targets)
