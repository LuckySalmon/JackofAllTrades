import winsound
import json
from collections.abc import Iterable
from random import choice

from panda3d.bullet import BulletWorld
from panda3d.core import Vec3, Mat3, Mat4
from direct.showbase.MessengerGlobal import messenger
from direct.task.TaskManagerGlobal import taskMgr

from moves import Move
from skeletons import Skeleton

enableSound = False
charList = ['regular', 'boxer', 'psycho', 'test']


class Character(object):
    def __init__(self,
                 attributes: dict[str, str],
                 xp: int = 0,
                 char_moves: Iterable[Move] = (),
                 skeleton: Skeleton | None = None):
        self.Name = attributes['name'].title()
        self.HP = int(attributes['hp'])
        self.Speed = int(attributes['speed'])
        self.Defense = int(attributes['defense'])
        self.XP = xp
        self.Level = 1
        self.update_level()
        self.moveList = {}
        for move in char_moves:
            self.add_move(move)
        self.skeleton = skeleton

    @classmethod
    def from_json(cls, file) -> 'Character':
        attributes = json.load(file)
        move_names = attributes.pop('basic_moves')
        move_set = []
        for move_name in move_names:
            with open(f'data\\moves\\{move_name}.json') as f:
                move = Move.from_json(f)
                move_set.append(move)
        skeleton = attributes.pop('skeleton')
        return cls(attributes, char_moves=move_set, skeleton=skeleton)

    def list_moves(self) -> dict[str, Move]:  # isn't this redundant?
        """Check what moves this character has and return a list of available moves."""
        print(self.moveList)
        return self.moveList

    def add_move(self, move: Move) -> None:
        """Attempt to add a move to this list of those available."""
        if len(self.moveList) < int(0.41 * self.Level + 4):
            # changed the above from <= as I'm assuming the formula is meant to be a cap, not one less than the cap
            self.moveList[move.name] = move
            if enableSound:
                winsound.Beep(600, 125)
                winsound.Beep(750, 100)
                winsound.Beep(900, 150)
        else:
            print("You have too many moves. Would you like to replace one?")
            if enableSound:
                winsound.Beep(600, 175)
                winsound.Beep(500, 100)

    def update_level(self) -> int:
        """Use a character's XP to increase their level."""
        while self.XP >= (threshold := self.Level * 1000):
            self.Level += 1
            self.XP -= threshold
        return self.Level


class Fighter(object):
    def __init__(self, character: Character, index: int = 0):
        self.Name = character.Name
        hp = character.HP
        self.BaseHP = hp
        self.HP = hp
        self.Speed = character.Speed
        self.Defense = character.Defense
        self.moveList = character.moveList
        with open(f'data\\skeletons\\{character.skeleton}.json') as skeleton_file:
            skeleton_params = json.load(skeleton_file)
        self.skeleton = Skeleton(skeleton_params)
        self.index = index

    @classmethod
    def from_json(cls, file) -> 'Fighter':
        character = Character.from_json(file)
        return cls(character)

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
                messenger.send('output_info', [self.index, f"{self.Name}'s {move.name} missed!"])
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
        damage = min(max(damage - self.Defense, 0), self.HP)    # TODO: Find and use a better formula
        self.HP -= damage
        messenger.send('output_info', [self.index, f'{self.Name} took {damage} damage!'])
        messenger.send('set_health_bar', [self.index, self.HP])
        if self.HP <= 0:
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
