import math
import random
from itertools import product

from direct.showbase.DirectObject import DirectObject
from direct.showbase.ShowBase import ShowBase
from panda3d.bullet import BulletDebugNode
from panda3d.core import Vec3

from characters import Fighter
import physics
import ui

gravity = 0

sides = ['l', 'r']
DefaultTargetPos = (1, 1, 0)
TARGETING = False
LEFT, RIGHT = -1, 1


def toggle_targeting():
    global TARGETING
    TARGETING = not TARGETING


class TargetMovingObject(DirectObject):
    def __init__(self):
        super().__init__()
        self.xyz = (0, 0, 0)
        self.targets = []
        bindings = (('7-repeat', '1-repeat'), ('8-repeat', '2-repeat'), ('9-repeat', '3-repeat'))
        for axis, keys in enumerate(bindings):
            for i, key in enumerate(keys):
                self.accept(key, self.modify_coordinate, [axis, 0.01 * (-1)**i])
        self.accept('4-repeat', self.scale_targets, [0.99])
        self.accept('6-repeat', self.scale_targets, [1.01])

    def update(self) -> None:
        x, y, z = self.xyz
        coordinates = [[x, y, z], [x, -y, z], [-x, -y, z], [-x, y, z]]
        self.targets.clear()
        targets = [Vec3(x, y, z) for x, y, z in coordinates]
        self.targets += targets

    def set_targets(self, x: float, y: float, z: float) -> list[float]:
        self.xyz = [x, y, z]
        self.update()
        return self.targets

    def modify_coordinate(self, axis: int, delta: float) -> None:
        self.xyz[axis] += delta
        self.update()

    def scale_targets(self, scale: float) -> None:
        for axis in range(3):
            self.xyz[axis] *= scale
        self.update()


class ShoulderMovingObject(DirectObject):
    def __init__(self, character_list: list[Fighter]):
        super().__init__()
        self.character_list = character_list
        bindings = [('q', 'e'), ('a', 'd'), ('z', 'c')]
        for axis, keys in enumerate(bindings):
            for i, key in enumerate(keys):
                self.accept(key, self.move_arms, [axis, (-1) ** i])
                self.accept(key + '-up', self.move_arms, [axis, 0])
        self.accept('s', self.arms_down)
        self.accept('r', self.bend_arms, [math.pi / 2])
        self.accept('v', self.bend_arms, [0.0])
        self.accept('p', self.print_angles)
        self.accept('space', toggle_targeting)

    def move_arms(self, axis: int, speed: float) -> None:
        for i, character in enumerate(self.character_list):
            character.skeleton.set_shoulder_motion(axis, speed)

    def bend_arms(self, angle: float) -> None:
        for character in self.character_list:
            for arm in character.skeleton.arm_l, character.skeleton.arm_r:
                arm.elbow.enableMotor(True)
                arm.elbow.setMotorTarget(angle, 0.5)
                arm.forearm.node().setActive(True, False)

    def arms_down(self) -> None:
        for character in self.character_list:
            character.skeleton.arms_down()

    def print_angles(self) -> None:
        for character in self.character_list:
            for arm in character.skeleton.arm_l, character.skeleton.arm_r:
                angles = [arm.shoulder.getAngle(i) for i in range(3)]
                print('angles: {:.4f}, {:.4f}, {:.4f}'.format(*angles))
                angles[2] *= -1
                c3, c2, c1 = [math.cos(angle) for angle in angles]
                s3, s2, s1 = [math.sin(angle) for angle in angles]
                calculated_point = Vec3(c1 * c3 * s2 + s1 * s3, -c2 * c3, -c1 * s3 + c3 * s1 * s2) * 0.375
                print('calculated bicep pos: ({: .4f}, {: .4f}, {: .4f})'.format(*calculated_point))
                actual_point = arm.bicep.getPos() - arm.position
                print('    actual bicep pos: ({: .4f}, {: .4f}, {: .4f})'.format(*actual_point))
                print()


class App(ShowBase):
    def __init__(self, fighters: list[Fighter]):
        super().__init__()

        self.clock = 0

        self.fighters = []
        self.buttons = []
        self.index = 0

        self.world = None
        self.debugNP = None

        self.targets = []

        self.ui = None
        self.selectedAction, self.selection = None, None

        self.start_battle(fighters)

    def start_battle(self, fighters: list[Fighter]) -> None:
        fighters.sort(key=lambda x: x.Speed, reverse=True)
        for fighter in fighters:
            fighter.HP = fighter.BaseHP
        self.fighters = fighters

        # Set up the World
        # The World
        self.world = physics.make_world(gravity, self.render)

        # Camera
        self.cam.setPos(0, -15, 2)
        self.cam.lookAt(0, 0, 0)

        # Characters
        fighters[0].insert(self.world, self.render, -1, (-2, 0))
        fighters[1].insert(self.world, self.render, 1, (2, 0))

        # Debug
        debug_node = BulletDebugNode('Debug')
        debug_node.showWireframe(True)
        debug_node.showConstraints(False)
        debug_node.showBoundingBoxes(False)
        debug_node.showNormals(False)
        self.debugNP = self.render.attachNewNode(debug_node)
        self.debugNP.show()
        self.world.setDebugNode(self.debugNP.node())
        debug_object = DirectObject()
        debug_object.accept('f1', self.toggle_debug)

        # Testing Controls
        shoulder_moving_object = ShoulderMovingObject(fighters)
        target_moving_object = TargetMovingObject()
        self.targets = target_moving_object.set_targets(*DefaultTargetPos)
        for i in range(3):
            shoulder_moving_object.move_arms(i, 0)

        self.taskMgr.add(self.update, 'update')

        # Set up GUI
        self.ui = ui.BattleInterface(self.fighters, self.use_action)

        self.query_action()

    def update(self, task) -> int:
        """Update the world using physics."""
        self.clock += 1
        if TARGETING and self.clock % 10 == 0:
            for (fighter, side), target in zip(product(self.fighters, sides), self.targets):
                fighter.skeleton.position_shoulder(side, target)
        return physics.update_physics(self.world, task)

    def toggle_debug(self) -> None:
        """Toggle debug display for physical objects."""
        if self.debugNP.isHidden():
            self.debugNP.show()
        else:
            self.debugNP.hide()

    def query_action(self) -> None:
        """Set up buttons for a player to choose an action."""
        fighter = self.fighters[self.index]
        self.ui.query_action(fighter, self.index, self.set_action)

    def set_action(self, fighter: Fighter, name: str) -> None:
        """Set an action to be selected."""
        i = self.index
        self.selectedAction = fighter.moveList[name]
        self.ui.output_info(i, self.selectedAction.show_stats())
        self.ui.select_action(i, name)
        self.selection = name

    def use_action(self) -> None:
        """Make the character use the selected action, then move on to the next turn."""
        self.ui.remove_query()
        user = self.fighters[self.index]
        name, move = self.selection, self.selectedAction

        # Result of move
        if move.get_accuracy() > random.randint(0, 99):
            damage = move.get_damage()
            if random.randint(1, 100) <= 2:
                damage *= 1.5
                print("Critical Hit!".format(user.Name, name, damage))
            self.ui.output_info(self.index, f"{user.Name}'s {name} hit for {damage} damage!")
        else:
            damage = 0
            self.ui.output_info(self.index, f"{user.Name}'s {name} missed!")

        # Move over to other character and apply damage
        self.index = (self.index + 1) % 2
        opponent = self.fighters[self.index]
        damage = min(max(damage - opponent.Defense, 0), opponent.HP)  # TODO: Find and use a better formula
        opponent.HP -= damage
        self.ui.apply_damage(self.index, damage, opponent.Name)

        # Move on to next step (KO or opponent response)
        if opponent.HP <= 0:
            self.ui.announce_win(user.Name)
            # I thought this would make the character fall, but it just glitches out
            self.fighters[self.index].skeleton.torso.node().setMass(1.0)
            self.fighters[self.index].skeleton.torso.node().setActive(True, False)
        else:
            self.query_action()
        # TODO: I would like to make this program focused entirely on graphics.
        #  I.e., other computations are handled externally and relevant results passed to functions from here.


def test() -> None:
    """Run a battle between two test characters for debug purposes."""
    filepath = 'data\\characters\\test.json'
    fighter_list = []
    for _ in range(2):
        with open(filepath) as file:
            fighter = Fighter.from_json(file)
            fighter_list.append(fighter)
    app = App(fighter_list)
    app.run()


if __name__ == "__main__":
    test()
