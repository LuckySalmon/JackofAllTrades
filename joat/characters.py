from __future__ import annotations

import json
import logging
import random
from collections.abc import Container, Mapping
from pathlib import Path
from typing import Any, Final, Protocol
from typing_extensions import Self

import attrs
from attrs import field
from direct.showbase.MessengerGlobal import messenger
from panda3d.bullet import BulletPersistentManifold
from panda3d.core import (
    GeomNode,
    LVecBase3,
    NodePath,
    PandaNode,
    PGFrameStyle,
    PGWaitBar,
    TransformState,
)

from . import arenas, debug, moves, stances
from .effects import Effect, StatusEffect
from .skeletons import Skeleton

_logger: Final = logging.getLogger(__name__)


def make_health_bar(fighter: Fighter) -> NodePath[PGWaitBar]:
    bar = PGWaitBar('Health Bar')
    bar.set_frame(-0.4, 0.4, 0, 0.1)
    bar.set_range(fighter.base_health)
    bar.set_value(fighter.health)

    frame_style = PGFrameStyle()
    frame_style.set_width(0, 0)
    frame_style.set_color(0.8, 0.8, 0.8, 1)
    frame_style.set_type(PGFrameStyle.T_flat)
    bar.set_frame_style(0, frame_style)

    bar_style = PGFrameStyle()
    bar_style.set_width(0, 0)
    bar_style.set_color(1, 0, 0, 1)
    bar_style.set_type(PGFrameStyle.T_flat)
    bar.set_bar_style(bar_style)

    bar_path = fighter.skeleton.core.attach_new_node(bar)
    bar_path.set_pos(0, 0, 1.1)
    bar_path.set_billboard_point_eye()
    return bar_path


class Action(Protocol):
    @property
    def name(self) -> str:
        raise NotImplementedError

    @property
    def valid_targets(self) -> Container[moves.Target]:
        raise NotImplementedError

    async def use(self, user: Fighter, using_on: Fighter) -> object:
        raise NotImplementedError


@attrs.define(kw_only=True)
class Character:
    name: str
    health: int
    speed: int
    strength: int
    defense: int
    moves: list[Action] = attrs.Factory(list)
    xp: int = field(default=0, init=False, repr=False)
    level: int = field(default=0, init=False, repr=False)

    def __str__(self) -> str:
        return f'{type(self).__name__} {self.name!r}'

    @classmethod
    def from_json(
        cls, attributes: dict[str, Any], *, move_dict: Mapping[str, Action]
    ) -> Self:
        move_names = attributes.pop('basic_moves')
        moves = [move_dict[name] for name in move_names]
        attributes.pop('trade')
        return cls(**attributes, moves=moves)

    def make_fighter(
        self, *, xform: TransformState = TransformState.make_identity()
    ) -> Fighter:
        with Path('data', 'skeletons', 'default.json').open() as f:
            skeleton_params: dict[str, dict[str, Any]] = json.load(f)
        skeleton = Skeleton.construct(
            skeleton_params,
            transform=xform,
            speed=(2 + self.speed) * 2,
            strength=self.strength * 1.5,
        )
        return Fighter(name=self.name, character=self, skeleton=skeleton)

    def add_move(self, move: Action) -> None:
        """Attempt to add a move to this list of those available."""
        # TODO: why this formula?
        if len(self.moves) < int(0.41 * self.level + 4):
            self.moves.append(move)
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


@attrs.define(kw_only=True)
class Fighter:
    name: str
    character: Character
    health: int = field(init=False)
    skeleton: Skeleton = field(repr=False)
    arena: arenas.Arena | None = None
    status_effects: list[StatusEffect] = field(factory=list, init=False)
    health_bar: NodePath[PGWaitBar] = field(init=False)

    @property
    def base_health(self) -> int:
        return self.character.health

    @property
    def speed(self) -> int:
        return self.character.speed

    @property
    def strength(self) -> int:
        return self.character.strength

    @property
    def defense(self) -> int:
        return self.character.defense

    @property
    def moves(self) -> list[Action]:
        return self.character.moves

    def __attrs_post_init__(self) -> None:
        self.health = self.base_health
        self.health_bar = make_health_bar(self)
        for part in self.skeleton.parts.values():
            part.node().python_tags.update(
                fighter=self,
                impact_callback=standard_impact_callback,
            )

    def __str__(self) -> str:
        return f'{type(self).__name__} {self.name!r}'

    def enter_arena(self, arena: arenas.Arena) -> None:
        self.arena = arena
        self.skeleton.enter_arena(arena)

    def exit_arena(self) -> None:
        if self.arena is not None:
            self.skeleton.exit_arena(self.arena)
            self.arena = None

    def set_stance(self, stance: stances.Stance) -> None:
        self.skeleton.stance = stance
        self.skeleton.assume_stance()

    def get_position_of(self, np: NodePath, inaccuracy: float = 0) -> LVecBase3:
        target_position = np.get_pos(self.skeleton.core)
        for i in range(3):
            scale = 1 - 2 * random.random()
            target_position[i] *= 1 + inaccuracy * scale
        return target_position

    async def use_move(self, move: Action, target: Fighter) -> None:
        _logger.debug(f'{self} used {move} on {target}')
        await move.use(self, target)

    def apply_damage(self, damage: int) -> None:
        if damage:
            _logger.debug(f'{self} took {damage} damage')
        self.health -= damage
        self.health_bar.node().set_value(self.health)
        messenger.send('output_info', [f'{self.name} took {damage} damage!'])
        if self.health <= 0:
            self.kill()

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

    def project_ring(self) -> NodePath[GeomNode]:
        assert self.arena is not None
        base_pos = self.skeleton.core.get_pos()
        base_pos.z = 0
        radius = self.speed
        node = debug.draw_path(
            base_pos + (+radius, +radius, 0),
            base_pos + (+radius, -radius, 0),
            base_pos + (-radius, -radius, 0),
            base_pos + (-radius, +radius, 0),
            base_pos + (+radius, +radius, 0),
        )
        node_path = NodePath(node)
        node_path.reparent_to(self.skeleton.core.parent)
        return node_path

    def kill(self) -> None:
        _logger.info(f'{self} died')
        self.skeleton.kill()


def standard_impact_callback(
    node: PandaNode,
    manifold: BulletPersistentManifold,
    *,
    min_impulse: float = 20,
) -> None:
    fighter: Fighter | None = node.python_tags.get('fighter')
    if fighter is None:
        return
    if node == manifold.node0:
        other_node = manifold.node1
    else:
        other_node = manifold.node0
    min_impulse = other_node.python_tags.get('min_impulse', min_impulse)
    for point in manifold.manifold_points:
        impulse = point.applied_impulse
        if impulse < min_impulse:
            continue
        multiplier: float = node.python_tags.get('damage_multiplier', 1)
        if not multiplier:
            # Don't do anything if the node is immune to damage.
            continue
        _logger.debug(
            f'{fighter} was hit in the {node.name} with an impulse of {impulse}'
        )
        damage = int(impulse * multiplier / (10 + fighter.defense))
        if damage:
            fighter.apply_damage(damage)
        effect: Effect | None = other_node.python_tags.pop('one_shot_effect', None)
        if effect is not None:
            _logger.debug(f'Applying {effect} to {fighter}')
            effect.apply(fighter)
