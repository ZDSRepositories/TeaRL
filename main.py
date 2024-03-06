from typing import Optional, List

import pygame, sys, random, time

pygame.init()

WIDTH, HEIGHT = 800-10, 400-19
screen = pygame.display.set_mode([WIDTH, HEIGHT])

FONT = pygame.font.SysFont("OCR A Extended", 18)
FONT_MENUS = pygame.font.SysFont("Lucida Console", 16)

LEVEL_W, LEVEL_H = 72, 20

# an enum if you squint
class actions:
    MOVE_N, MOVE_NE, MOVE_E, MOVE_SE, MOVE_S, MOVE_SW, MOVE_W, MOVE_NW, MOVE_DOWN = [i for i in range(9)]
    tile_move_actions = [MOVE_N, MOVE_NE, MOVE_E, MOVE_SE, MOVE_S, MOVE_SW, MOVE_W, MOVE_NW]

class directions:
    deltas =[[0, -1], [1, -1], [1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0], [-1, -1]]

move_keybinds = {pygame.K_UP:actions.MOVE_N, pygame.K_DOWN:actions.MOVE_S,
                 pygame.K_LEFT:actions.MOVE_W, pygame.K_RIGHT:actions.MOVE_E,
                 pygame.K_w: actions.MOVE_N, pygame.K_s: actions.MOVE_S,
                 pygame.K_a: actions.MOVE_W, pygame.K_d: actions.MOVE_E,
                 pygame.K_q: actions.MOVE_NW, pygame.K_e: actions.MOVE_NE,
                 pygame.K_z: actions.MOVE_SW, pygame.K_c: actions.MOVE_SE,
                 }
def dist(v1, v2):
    return ((v1[0]-v2[0])**2 + (v1[1]-v2[1])**2)**(1/2)

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

    def act(self, action, direct_object = None):
        if action in actions.tile_move_actions:
            delta = directions.deltas[action]
            newpos = self.x + delta[0], self.y + delta[1]
            if self.parent_level.valid_coords(newpos) and self.parent_level.get_tile(newpos).is_passable():
                self.move_to(newpos)


    def add_item(self, item):
        if not item in self.inventory:
            self.inventory.append(item)

    def remove_item(self, item):
        if item in self.inventory:
            self.inventory.remove(item)

    def pick_up(self):
        if self.tile.item:
            self.add_item(self.tile.item)
            self.tile.clear_item()

    def drop(self, item) -> bool:
        # tiles can only have one item, so this could fail
        if not self.tile.item:
            self.tile.item = item
            self.inventory.remove(item)
            return True
        return False

    def rendered(self):
        return FONT.render(self.char, False, [255, 255, 255], [0, 0, 0])

class Item:
    def __init__(self, name, char):
        self.name = name
        self.char = char
        self.tile = None

    def rendered(self) -> pygame.Surface:
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

    def set_item(self, item: Item):
        self.clear_item()
        self.item = item
        item.tile = self

    def clear_item(self):
        if self.item:
            self.item.tile = None
        self.item = None

    def is_passable(self):
        return self.passable and not self.unit

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
            if self.get_tile([walkerx, walkery]).name == "wall":
                self.set_tile(walkerx, walkery, Tile(".", True, "floor", walkerx, walkery))
                floorcount += 1

            walkerx = min(max(walkerx + random.choice([-1,-1, 0, 1, 1]), 0), self.ncols-2)
            walkery = min(max(walkery + random.choice([-1,0, 1]), 0), self.nrows - 2)
        print("generation done")

    def place_unit(self, unit, pos):
        #print(f"placing {unit.name} at {pos}")
        tile = self.get_tile(pos)
        #print(f"tile at {pos} is {tile}")
        try:
            tile.set_unit(unit)
        except: pass

    def move_unit(self, unit, newpos) -> bool:
        # returns True on success, False on failure
        if not unit.parent_level == self:
            return False
        if not self.valid_coords(newpos):
            return False
        unit.tile.clear_unit()
        self.place_unit(unit, newpos)
        return True

    def valid_coords(self, coords):
        return (coords[0] >= 0 and coords[0] < self.ncols) and \
               (coords[1] >= 0 and coords[1] < self.nrows)

    def render(self, surf):
        for row in self.tilemap:
            for tile in row:
                rendered = tile.rendered()
                surf.blit(rendered, [tile.x*rendered.get_width(), tile.y*rendered.get_height()])

    def get_tile(self, pos) -> [Optional[Tile]]:
        #try:
        #print(f"getting tile at {x, y}")
        return self.tilemap[pos[1]][pos[0]]
        #except:
        #    return None

    def set_tile(self, x, y, new_tile):
        try:
            self.tilemap[y][x] = new_tile
            return True
        except:
            return False

class GameRoot:
    def __init__(self, level: Level, player: Unit):
        self.level = level
        self.player = player
        self.active_modal = None

    def handle(self, ev):
        if self.active_modal:
            self.active_modal.handle(ev)
        else:
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key in move_keybinds:
                    self.player.act(move_keybinds[event.key])
                if ev.key == pygame.K_i:
                    i = InventoryWindow(self)
                    self.set_modal(i)
                if ev.key == pygame.K_g:
                    self.player.pick_up()

    def render(self, surf:pygame.Surface):
        self.level.render(surf)
        if self.active_modal:
            rendered:pygame.Surface = self.active_modal.rendered()
            centered_rect = rendered.get_rect()
            centered_rect.center = surf.get_rect().center
            surf.blit(rendered, centered_rect)

    def set_modal(self, modal):
        self.active_modal = modal
        self.active_modal.parent = self

    def clear_modal(self):
        self.active_modal.parent = None
        self.active_modal = None


class InventoryWindow:
    def __init__(self, parent:GameRoot):
        self.parent = parent

    def rendered(self) -> pygame.Surface:
        surf_rect = pygame.Rect([0,0,screen.get_width()*0.8, screen.get_height()*0.8])
        surf_rect.centerx, surf_rect.centery = screen.get_rect().centerx, screen.get_rect().centery
        surf = pygame.Surface([surf_rect.width, surf_rect.height])
        surf.fill([0,0,0])
        return surf

    def handle(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN:
            self.close()

    def close(self):
        self.parent.clear_modal()
        """
        items = self.parent.player.inventory
        max_columns = len(items) // 5
        for item in items:
            pass
        """

lev = Level(72, 20)
lev.generate(int((72*20)*0.3))

player = Unit("player", 10, 10, "@", lev.ncols // 2, lev.nrows // 2, lev)
mob =    Unit("goblin", 10, 10, "g", player.x+1, player.y+1, lev)
money = Item("money", "$")
moneytile = lev.get_tile([player.x, player.y-1])
moneytile.set_item(money)
moneytile.char, moneytile.passable = ".", True
player.set_level(lev, [player.x, player.y])
mob.set_level(lev, [player.x+1, player.y+1])

game = GameRoot(lev, player)
clock = pygame.time.Clock()

while True:
    for event in pygame.event.get():
        game.handle(event)
    screen.fill([0,0,0])
    game.render(screen)

    pygame.display.flip()
    #player.move_to([player.x + 1, player.y])
    clock.tick(60)



