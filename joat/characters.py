from __future__ import annotations

import json
import logging
import random
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from direct.gui.DirectWaitBar import DirectWaitBar
from direct.showbase import ShowBaseGlobal
from direct.showbase.MessengerGlobal import messenger
from panda3d.bullet import BulletPersistentManifold, BulletWorld
from panda3d.core import AsyncTaskPause, CollideMask, Mat3, Mat4, PandaNode, Vec3

from . import physics, stances
from .moves import Move, StatusEffect
from .skeletons import Skeleton

if TYPE_CHECKING:
    from _typeshed import SupportsRead

_logger: Final = logging.getLogger(__name__)


@dataclass(kw_only=True)
class Character:
    name: str = field(kw_only=False)
    hp: int
    speed: int
    strength: int
    defense: int
    moves: dict[str, Move] = field(default_factory=dict, repr=False)
    skeleton: str = field(default='default', repr=False)
    xp: int = field(default=0, init=False, repr=False)
    level: int = field(default=0, init=False, repr=False)

    def __str__(self) -> str:
        return f'{type(self).__name__} {self.name!r}'

    @classmethod
    def from_json(cls, file: SupportsRead[str | bytes]) -> Character:
        attributes = json.load(file)
        move_names = attributes.pop('basic_moves')
        moves = {}
        for move_name in move_names:
            path = Path('data', 'moves', move_name).with_suffix('.json')
            if path.exists():
                with path.open() as f:
                    move = Move.from_json(f)
                moves[move_name] = move
        attributes.pop('trade')
        return cls(**attributes, moves=moves)

    def add_move(self, move: Move) -> None:
        """Attempt to add a move to this list of those available."""
        # TODO: why this formula?
        if len(self.moves) < int(0.41 * self.level + 4):
            self.moves[move.name] = move
            # winsound.Beep(600, 125)
            # winsound.Beep(750, 100)
            # winsound.Beep(900, 150)
        else:
            # TODO: actually handle this case
            print("You have too many moves. Would you like to replace one?")
            # winsound.Beep(600, 175)
            # winsound.Beep(500, 100)

    def update_level(self) -> None:
        """Use the character's XP to increase their level."""
        while self.xp >= (threshold := self.level * 1000):
            self.level += 1
            self.xp -= threshold


@dataclass(kw_only=True)
class Fighter:
    name: str = field(kw_only=False)
    base_hp: int
    hp: int = field(init=False)
    speed: int
    strength: int
    defense: int
    moves: dict[str, Move] = field(repr=False)
    skeleton: Skeleton = field(repr=False)
    world: BulletWorld
    index: int = field(default=0, repr=False)
    status_effects: list[StatusEffect] = field(default_factory=list, init=False)
    health_bar: DirectWaitBar = field(init=False)

    def __post_init__(self) -> None:
        self.hp = self.base_hp
        self.health_bar = DirectWaitBar(
            parent=self.skeleton.core,
            range=self.base_hp,
            value=self.hp,
            pos=(0, 0, 1.1),
            frameSize=(-0.4, 0.4, 0, 0.1),
        )
        self.health_bar.set_billboard_point_eye()
        for part in self.skeleton.parts.values():
            part.node().python_tags.update(
                {
                    'fighter': self,
                    'impact_callback': damage_callback,
                }
            )

    def __str__(self) -> str:
        return f'{type(self).__name__} {self.name!r} ({self.index})'

    @classmethod
    def from_character(
        cls, character: Character, world: BulletWorld, index: int = 0
    ) -> Fighter:
        path = Path('data', 'skeletons', character.skeleton)
        with path.with_suffix('.json').open() as f:
            skeleton_params: dict[str, Any] = json.load(f)
        side = 1 if index else -1
        offset = Vec3(-0.5, 0, 0) if index == 0 else Vec3(0.5, 0, 0)
        rotation = Mat3(-side, 0, 0, 0, -side, 0, 0, 0, 1)
        coord_xform = Mat4(rotation, offset)
        skeleton = Skeleton.construct(
            skeleton_params,
            world,
            coord_xform,
            (2 + character.speed) * 2,
            character.strength * 1.5,
        )
        skeleton.parts['head'].set_collide_mask(CollideMask.bit(index))
        return cls(
            character.name,
            base_hp=character.hp,
            speed=character.speed,
            strength=character.strength,
            defense=character.defense,
            moves=character.moves,
            skeleton=skeleton,
            index=index,
            world=world,
        )

    @classmethod
    def from_json(
        cls,
        file: SupportsRead[str | bytes],
        world: BulletWorld,
        index: int = 0,
    ) -> Fighter:
        character = Character.from_json(file)
        return cls.from_character(character, world, index)

    def set_stance(self, stance: stances.Stance) -> None:
        self.skeleton.stance = stance
        self.skeleton.assume_stance()

    async def use_move(self, move: Move, target: Fighter) -> None:
        _logger.debug(f'{self} used {move} on {target}')
        if move.using == 'arm_right':
            arm = self.skeleton.right_arm
        elif move.using == 'arm_left':
            arm = self.skeleton.left_arm
        elif not move.is_projectile:
            move.apply(self, target)
            return
        else:
            arm = None

        target_part = target.skeleton.parts[move.target_part]
        target_position = target_part.get_pos(self.skeleton.core)
        for i in range(3):
            scale = 1 - 2 * random.random()
            inaccuracy = 1 - move.accuracy / 100
            target_position[i] *= 1 + inaccuracy * scale

        if move.is_projectile:
            render = ShowBaseGlobal.base.render
            if arm is None:
                using_part = self.skeleton.parts[move.using]
                offset = Vec3(0, 0, 0)
            else:
                arm.target_point = target_position - arm.origin
                await AsyncTaskPause(1 / (1 + self.speed) / 8)
                using_part = arm.forearm
                offset = Vec3(0, -0.25, 0)
            global_target_position = render.get_relative_point(
                self.skeleton.core, target_position
            )
            from_position = render.get_relative_point(using_part, offset)
            projectile = physics.spawn_projectile(
                name=move.name,
                instant_effects=move.instant_effects,
                status_effects=move.status_effects,
                world=self.world,
                position=from_position,
                velocity=physics.required_projectile_velocity(
                    global_target_position - from_position,
                    self.strength * 4,
                ),
                collision_mask=~using_part.get_collide_mask(),
            )
            self.skeleton.assume_stance()
            await AsyncTaskPause(0.2 / self.strength)
            if not projectile.is_empty():
                projectile.set_collide_mask(CollideMask.all_on())
            return

        assert arm is not None
        fist = arm.forearm.node()
        current_callback = fist.python_tags.get('impact_callback')

        def temporary_impact_callback(
            node: PandaNode, manifold: BulletPersistentManifold
        ) -> None:
            if node == manifold.node0:
                other_node = manifold.node1
            else:
                other_node = manifold.node0
            other_fighter = other_node.python_tags.get('fighter')
            if other_fighter is target and any(
                p.distance < 0.01 for p in manifold.manifold_points
            ):
                _logger.debug(f'{move} landed')
                move.apply(self, target, True)
                node.python_tags['impact_callback'] = current_callback
            if current_callback is not None:
                current_callback(node, manifold)

        fist.python_tags['impact_callback'] = temporary_impact_callback
        arm.target_point = target_position - arm.origin
        await AsyncTaskPause(1 / (1 + self.speed))
        self.skeleton.assume_stance()
        fist.python_tags['impact_callback'] = current_callback

    def apply_damage(self, damage: int) -> None:
        if damage:
            _logger.debug(f'{self} took {damage} damage')
        self.hp -= damage
        self.health_bar['value'] = self.hp
        messenger.send('output_info', [f'{self.name} took {damage} damage!'])
        if self.hp <= 0:
            self.kill()

    def copy_effects(self, effects: Iterable[StatusEffect]) -> None:
        for effect in effects:
            self.add_effect(replace(effect))

    def add_effect(self, effect: StatusEffect) -> None:
        _logger.debug(f'Added {effect} to {self}')
        effect.on_application(self)
        self.status_effects.append(effect)

    def apply_current_effects(self) -> None:
        if self.status_effects:
            _logger.debug(f'Applying active effects to {self} ({self.status_effects})')
        new_effects: list[StatusEffect] = []
        for effect in self.status_effects:
            effect.on_turn(self)
            effect.duration -= 1
            if effect.is_active():
                new_effects.append(effect)
            else:
                effect.on_removal(self)
        self.status_effects = new_effects

    def kill(self) -> None:
        _logger.info(f'{self} died')
        self.skeleton.kill()


def damage_callback(
    node: PandaNode,
    manifold: BulletPersistentManifold,
    *,
    min_damaging_impulse: float = 20,
) -> None:
    fighter: Fighter | None = node.python_tags.get('fighter')
    if fighter is None:
        return
    for point in manifold.manifold_points:
        impulse = point.applied_impulse
        if impulse < min_damaging_impulse:
            continue
        multiplier: float = node.python_tags.get('damage_multiplier', 1)
        damage = int(impulse * multiplier / (10 + fighter.defense))
        if not damage:
            continue
        _logger.debug(
            f'{fighter} was hit in the {node.name} with an impulse of {impulse}'
        )
        fighter.apply_damage(damage)
