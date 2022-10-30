import json
import winsound
from dataclasses import dataclass, field
from pathlib import Path
from random import choice
from typing import Any

from direct.showbase.MessengerGlobal import messenger
from direct.task.TaskManagerGlobal import taskMgr
from panda3d.bullet import BulletWorld
from panda3d.core import Mat3, Mat4, Vec3

from .moves import Move, StatusEffect
from .skeletons import Skeleton

SOUND_ENABLED = False


@dataclass
class Character:
    name: str
    hp: int
    speed: int
    strength: int
    defense: int
    moves: dict[str, Move] = field(default_factory=dict)
    skeleton: str = 'default'
    xp: int = field(default=0, init=False)
    level: int = field(default=0, init=False)

    @classmethod
    def from_json(cls, file) -> 'Character':
        attributes = json.load(file)
        move_names = attributes.pop('basic_moves')
        moves = {}
        for move_name in move_names:
            try:
                with Path('data', 'moves',
                          move_name).with_suffix('.json').open() as f:
                    move = Move.from_json(f)
                    moves[move_name] = move
            except FileNotFoundError:
                continue
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


@dataclass
class Fighter:
    name: str
    base_hp: int
    hp: int = field(init=False)
    speed: int
    strength: int
    defense: int
    moves: dict[str, Move]
    skeleton: Skeleton
    index: int = 0
    status_effects: list[StatusEffect] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self.hp = self.base_hp

    @classmethod
    def from_character(cls, character: Character,
                       world: BulletWorld,
                       index: int = 0) -> 'Fighter':
        with Path('data', 'skeletons',
                  character.skeleton).with_suffix('.json').open() as f:
            skeleton_params: dict[str, Any] = json.load(f)
        side = 1 if index else -1
        offset = Vec3(-0.75, 0, 0) if index == 0 else Vec3(0.75, 0, 0)
        rotation = Mat3(-side, 0, 0, 0, -side, 0, 0, 0, 1)
        coord_xform = Mat4(rotation, offset)
        skeleton = Skeleton.construct(skeleton_params, world, coord_xform,
                                      character.speed, character.strength)
        return cls(character.name,
                   character.hp,
                   character.speed,
                   character.strength,
                   character.defense,
                   character.moves,
                   skeleton,
                   index)

    @classmethod
    def from_json(cls, file, world: BulletWorld, index: int = 0) -> 'Fighter':
        character = Character.from_json(file)
        return cls.from_character(character, world, index)

    def use_move(self, move: Move,
                 target: 'Fighter',
                 world: BulletWorld) -> None:
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

        def reset(_):
            self.skeleton.set_arm_target(side, current_position)
            messenger.send('next_turn')

        def use_move(task):
            if task.time >= 1:
                messenger.send(
                    'output_info',
                    [self.index, f"{self.name}'s {move.name} missed!"]
                )
                return task.done

            contact_result = world.contact_test_pair(fist.node(),
                                                     target_part.node())
            for contact in contact_result.get_contacts():
                manifold_point = contact.get_manifold_point()
                if abs(manifold_point.distance) > 0.01:
                    continue
                move.apply(self, target, True)
                return task.done

            return task.cont

        self.skeleton.set_arm_target(side, target_position, False)
        taskMgr.add(use_move, 'use_move', uponDeath=reset)

    def apply_damage(self, damage: int) -> None:
        # TODO: Find and use a better formula
        damage = min(max(damage - self.defense, 0), self.hp)
        self.hp -= damage
        messenger.send(
            'output_info',
            [self.index, f'{self.name} took {damage} damage!']
        )
        messenger.send('set_health_bar', [self.index, self.hp])
        if self.hp <= 0:
            self.kill()

    def add_effect(self, effect: StatusEffect) -> None:
        self.status_effects.append(effect)

    def apply_current_effects(self) -> None:
        new_effects: list[StatusEffect] = []
        for effect in self.status_effects:
            effect.on_turn(self)
            effect.duration -= 1
            if effect.is_active():
                new_effects.append(effect)
        self.status_effects = new_effects

    def kill(self) -> None:
        self.skeleton.kill()
