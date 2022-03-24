import json
import winsound
from random import choice

from panda3d.bullet import BulletWorld
from panda3d.core import Vec3, Mat3, Mat4
from direct.showbase.MessengerGlobal import messenger
from direct.task.TaskManagerGlobal import taskMgr

from moves import Move
from skeletons import Skeleton

SOUND_ENABLED = False


class Character:
    def __init__(self,
                 name: str,
                 hp: int,
                 speed: int,
                 defense: int,
                 moves: dict[str, Move] | None = None,
                 skeleton: str = 'default'):
        self.name = name.title()
        self.hp = hp
        self.speed = speed
        self.defense = defense
        self.xp = 0
        self.level = 0
        self.moves = moves or {}
        self.skeleton = skeleton

    @classmethod
    def from_json(cls, file) -> 'Character':
        attributes = json.load(file)
        move_names = attributes.pop('basic_moves')
        moves = {}
        for move_name in move_names:
            with open(f'data\\moves\\{move_name}.json') as f:
                move = Move.from_json(f)
                moves[move_name] = move
        attributes.pop('trade')
        return cls(**attributes, moves=moves)

    def add_move(self, move: Move) -> None:
        """Attempt to add a move to this list of those available."""
        if len(self.moves) < int(0.41 * self.level + 4):     # TODO: why this formula?
            self.moves[move.name] = move
            if SOUND_ENABLED:
                winsound.Beep(600, 125)
                winsound.Beep(750, 100)
                winsound.Beep(900, 150)
        else:
            print("You have too many moves. Would you like to replace one?")    # TODO: actually handle this case
            if SOUND_ENABLED:
                winsound.Beep(600, 175)
                winsound.Beep(500, 100)

    def update_level(self) -> None:
        """Use the character's XP to increase their level."""
        while self.xp >= (threshold := self.level * 1000):
            self.level += 1
            self.xp -= threshold


class Fighter:
    def __init__(self,
                 name: str,
                 base_hp: int,
                 speed: int,
                 defense: int,
                 moves: dict[str, Move],
                 skeleton: Skeleton,
                 index: int = 0):
        self.name = name
        self.base_hp = base_hp
        self.hp = base_hp
        self.speed = speed
        self.defense = defense
        self.moves = moves
        self.skeleton = skeleton
        self.index = index

    @classmethod
    def from_character(cls, character: Character, index: int = 0) -> 'Fighter':
        with open(f'data\\skeletons\\{character.skeleton}.json') as f:
            skeleton_params = json.load(f)
        skeleton = Skeleton(skeleton_params)
        return cls(character.name,
                   character.hp,
                   character.speed,
                   character.defense,
                   character.moves,
                   skeleton,
                   index)

    @classmethod
    def from_json(cls, file, index: int = 0) -> 'Fighter':
        character = Character.from_json(file)
        return cls.from_character(character, index)

    def use_move(self, move: Move, target: 'Fighter', world: BulletWorld) -> None:
        target_part = target.skeleton.parts.get(move.target)
        if target_part is None:
            move.apply(self, target)
            messenger.send('next_turn')
            return

        side = choice((-1, 1))
        fist = self.skeleton.parts['forearm_left' if side == -1 else 'forearm_right']
        current_position = self.skeleton.get_arm_target(side)
        target_position = target_part.getNetTransform().getPos()

        def reset(_):
            self.skeleton.set_arm_target(side, current_position)
            messenger.send('next_turn')

        def use_move(task):
            if task.time >= 1:
                messenger.send('output_info', [self.index, f"{self.name}'s {move.name} missed!"])
                return task.done

            contacts = world.contactTest(fist.node()).getContacts()
            for contact in contacts:
                manifold_point = contact.getManifoldPoint()
                if abs(manifold_point.distance) > 0.01:
                    continue
                if contact.getNode1() == target_part.node():
                    move.apply(self, target, True)
                    return task.done

            return task.cont

        self.skeleton.set_arm_target(side, target_position, False)
        taskMgr.add(use_move, 'use_move', uponDeath=reset)

    def apply_damage(self, damage: int) -> None:
        damage = min(max(damage - self.defense, 0), self.hp)    # TODO: Find and use a better formula
        self.hp -= damage
        messenger.send('output_info', [self.index, f'{self.name} took {damage} damage!'])
        messenger.send('set_health_bar', [self.index, self.hp])
        if self.hp <= 0:
            self.kill()

    def insert(self, world: BulletWorld, pos: tuple[float, float]) -> None:
        """Place the character in the world."""
        side = 1 if self.index else -1
        x, y = pos
        offset = Vec3(x, y, 0)
        rotation = Mat3(-side, 0, 0, 0, -side, 0, 0, 0, 1)
        coord_xform = Mat4(rotation, offset)

        self.skeleton.insert(world, coord_xform)

    def kill(self) -> None:
        self.skeleton.kill()
