from typing import Optional, List

import pygame, sys, random, time

pygame.init()

WIDTH, HEIGHT = 800-10, 400-19
screen = pygame.display.set_mode([WIDTH, HEIGHT])

FONT = pygame.font.SysFont("OCR A Extended", 18)

LEVEL_W, LEVEL_H = 72, 20

# an enum if you squint
class actions:
    MOVE_N, MOVE_NE, MOVE_E, MOVE_SE, MOVE_S, MOVE_SW, MOVE_W, MOVE_NW, MOVE_DOWN = [i for i in range(9)]
    tile_move_actions = [MOVE_N, MOVE_NE, MOVE_E, MOVE_SE, MOVE_S, MOVE_SW, MOVE_W, MOVE_NW]

class directions:
    deltas =[[0, -1], [1, -1], [1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0], [-1, -1]]

class Unit:
    def __init__(self, name, hp, maxhp, char, x, y, parent_level):
        self.name = name
        self.hp = hp
        self.maxhp = maxhp
        self.char = char
        self.x, self.y = x, y
        self.set_level(parent_level)
        self.tile = None
        self.inventory = []

    def set_level(self, new_level, pos = None):
        self.parent_level = new_level
        new_level.place_unit(self, pos if pos else [self.x, self.y])


    def move_to(self, pos):
        try:
            self.parent_level.move_unit(self, pos)
            return True
        except IndexError:
            return False

    def act(self, action):
        if action in actions.tile_move_actions:
            delta = directions.deltas[action]
            newpos = self.x + delta[0], self.y + delta[1]

    def add_item(self, item):
        if not item in self.inventory:
            self.inventory.append(item)

    def remove_item(self, item):
        if item in self.inventory:
            self.inventory.remove(item)


    def rendered(self):
        return FONT.render(self.char, False, [255, 255, 255], [0, 0, 0])

class Tile:
    def __init__(self, char, passable, name, x, y, item=None, unit=None):
        self.char = char
        self.passable = passable
        self.name = name
        self.x, self.y = x, y
        self.item = item
        self.unit = unit

    def set_unit(self, unit):
        unit.tile = self
        unit.x, unit.y = self.x, self.y
        self.unit = unit

    def clear_unit(self):
        self.unit.tile = None
        self.unit = None

    def rendered(self):
        if self.unit:
            return self.unit.rendered()
        elif self.item:
            return self.item.rendered()
        else:
            return FONT.render(self.char, False, [255, 255, 255], [0, 0, 0])

class Level:
    def __init__(self, cols, rows):
        self.ncols = cols
        self.nrows = rows
        self.tilemap = [[None for c in range(cols)] for r in range(rows)]

    def generate(self, floorgoal):
        self.tilemap = [[Tile("#", False, "wall", c, r) for c in range(self.ncols)] for r in range(self.nrows)]
        walkerx, walkery = self.ncols // 2, self.nrows // 2
        minx, miny, maxx, maxy = walkerx, walkery, walkerx, walkery
        floorcount = 0

        while floorcount < floorgoal:
            if self.get_tile(walkerx, walkery).name == "wall":
                self.set_tile(walkerx, walkery, Tile(".", True, "floor", walkerx, walkery))
                floorcount += 1

            walkerx = min(max(walkerx + random.choice([-1,-1, 0, 1, 1]), 0), self.ncols-2)
            walkery = min(max(walkery + random.choice([-1,0, 1]), 0), self.nrows - 2)
        print("generation done")

    def place_unit(self, unit, pos):
        #print(f"placing {unit.name} at {pos}")
        tile = self.get_tile(pos[0], pos[1])
        #print(f"tile at {pos} is {tile}")
        try:
            tile.set_unit(unit)
        except: pass

    def move_unit(self, unit, newpos):
        if not unit.parent_level == self:
            raise ValueError(f"unit {unit.name} not on level")
        unit.tile.clear_unit()
        self.place_unit(unit, newpos)

    def render(self, surf):
        for row in self.tilemap:
            for tile in row:
                rendered = tile.rendered()
                surf.blit(rendered, [tile.x*rendered.get_width(), tile.y*rendered.get_height()])

    def get_tile(self, x, y) -> [Optional[Tile]]:
        #try:
        #print(f"getting tile at {x, y}")
        return self.tilemap[y][x]
        #except:
        #    return None

    def set_tile(self, x, y, new_tile):
        try:
            self.tilemap[y][x] = new_tile
            return True
        except:
            return False

lev = Level(72, 20)
lev.generate(int((72*20)*0.4))

player = Unit("player", 10, 10, "@", lev.ncols // 2, lev.nrows // 2, lev)
player.set_level(lev, [player.x, player.y])
player.move_to([player.x+1, player.y])

clock = pygame.time.Clock()
t = 0
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    lev.render(screen)
    pygame.display.flip()
    player.move_to([player.x + 1, player.y])
    clock.tick(2)



