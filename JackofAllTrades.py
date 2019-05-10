# Goals - running player atributes - Battles - move lists - hp
# second goals - Game Rewards - Matchmaking - Graphics - text - voices

import random
import pygame

class Moves:
    #each move needs to return dmg range, accuracy range, and 1 other status affect
    def __init__(self, Dmg, Acc, Sfx):
        self.Sfx = Sfx
        self.Dmg = Dmg
        self.Acc = Acc

    def getDamage(self):
        return random.randint(self.Dmg[0], self.Dmg[1])
    def getAccuracy(self):
        return random.randint(self.Acc[0], self.Acc[1])
    def getStat(self):
        return self.Sfx
    
    
class Character:
    # Set class, health, defence, speed, move modifiers: dammage multiplyer, Lv requirements, etc.
    def __init__(self, MaxHealth, Defence, Speed, Level, XP)
        #starting Level should be 1 with 0 XP
        self.XP = XP
        self.Level = Level
        #HP scales with LV, can be modifyed 
        self.MaxHP = MaxHealth
        #defence should be a % reduction of DMG
        self.Defence = Defence
        #Speed is who goes first and can be a modifyer to Dmg 
        self.Speed = Speed
    def CheckLV(XP):
        #each level should be exponetionally more XP
        Level = 
    AvailableMoves = []
    
    
    
    
