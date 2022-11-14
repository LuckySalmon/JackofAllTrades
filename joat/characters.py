from __future__ import annotations

import json
import logging
import winsound
from dataclasses import dataclass, field
from pathlib import Path
from random import choice
from typing import TYPE_CHECKING, Any, Final, Literal

from direct.showbase.MessengerGlobal import messenger
from direct.task import Task
from direct.task.TaskManagerGlobal import taskMgr
from panda3d.bullet import BulletWorld
from panda3d.core import Mat3, Mat4, Vec3

from .moves import Move, StatusEffect
from .skeletons import Skeleton

if TYPE_CHECKING:
    from _typeshed import SupportsRead

_logger: Final = logging.getLogger(__name__)

SOUND_ENABLED = False


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
            if SOUND_ENABLED:
                winsound.Beep(600, 125)
                winsound.Beep(750, 100)
                winsound.Beep(900, 150)
        else:
            # TODO: actually handle this case
            print("You have too many moves. Would you like to replace one?")
            if SOUND_ENABLED:
                winsound.Beep(600, 175)
                winsound.Beep(500, 100)

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
    index: int = field(default=0, repr=False)
    status_effects: list[StatusEffect] = field(
        default_factory=list, init=False
    )

    def __post_init__(self) -> None:
        self.hp = self.base_hp
        for part in self.skeleton.parts.values():
            part.node().python_tags['fighter'] = self

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
            character.strength,
        )
        return cls(
            character.name,
            base_hp=character.hp,
            speed=character.speed,
            strength=character.strength,
            defense=character.defense,
            moves=character.moves,
            skeleton=skeleton,
            index=index,
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

    def use_move(
        self, move: Move, target: Fighter, world: BulletWorld
    ) -> None:
        _logger.debug(f'{self} used {move} on {target}')
        target_part = target.skeleton.parts.get(move.target_part)
        if target_part is None:
            move.apply(self, target)
            messenger.send('next_turn')
            return

        side = choice((-1, 1))
        fist = self.skeleton.parts[
            'forearm_left' if side == -1 else 'forearm_right'
        ]
        current_position = self.skeleton.get_arm_target(side)
        target_position = target_part.get_net_transform().get_pos()
        target_node = target_part.node()

        def reset(_: object) -> None:
            self.skeleton.set_arm_target(side, current_position)
            messenger.send('next_turn')

        if not (move.instant_effects or move.status_effects):
            self.skeleton.set_arm_target(side, target_position, False)
            taskMgr.do_method_later(1 / (1 + self.speed), reset, 'reset_move')
            return

        def use_move(task: Task.Task) -> Literal[0, 1]:
            if task.time >= 1:
                _logger.debug(f'{move} missed')
                messenger.send(
                    'output_info',
                    [self.index, f"{self.name}'s {move.name} missed!"],
                )
                return Task.done

            contact_result = world.contact_test_pair(fist.node(), target_node)
            for contact in contact_result.contacts:
                if abs(contact.manifold_point.distance) > 0.01:
                    continue
                _logger.debug(f'{move} landed')
                move.apply(self, target, True)
                return Task.done

            return task.cont

        self.skeleton.set_arm_target(side, target_position, False)
        taskMgr.add(use_move, 'use_move', uponDeath=reset)

    def apply_damage(self, damage: int) -> None:
        if damage:
            _logger.debug(f'{self} took {damage} damage')
        self.hp -= damage
        messenger.send(
            'output_info', [self.index, f'{self.name} took {damage} damage!']
        )
        messenger.send('set_health_bar', [self.index, self.hp])
        if self.hp <= 0:
            self.kill()

    def add_effect(self, effect: StatusEffect) -> None:
        _logger.debug(f'Added {effect} to {self}')
        self.status_effects.append(effect)

    def apply_current_effects(self) -> None:
        if self.status_effects:
            _logger.debug(
                f'Applying active effects to {self} ({self.status_effects})'
            )
        new_effects: list[StatusEffect] = []
        for effect in self.status_effects:
            effect.on_turn(self)
            effect.duration -= 1
            if effect.is_active():
                new_effects.append(effect)
        self.status_effects = new_effects

    def kill(self) -> None:
        _logger.info(f'{self} died')
        self.skeleton.kill()
