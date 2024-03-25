from typing import Optional, List

import pygame, sys, random, textwrap
from bres import bresenham

pygame.init()

FONT = pygame.font.SysFont("OCR A Extended", 18)
FONT_MENUS = pygame.font.SysFont("Lucida Console", 16)
LEVEL_W, LEVEL_H = 72, 20
WIDTH, HEIGHT = LEVEL_W*FONT.render("#", True, [0,0,0]).get_width(), (LEVEL_H+1)*FONT.get_height()
LEVEL_FLOORCOUNT = int((LEVEL_W*LEVEL_H)*0.3)

screen = pygame.display.set_mode([WIDTH, HEIGHT])


LCLICK, RCLICK = 1, 3
THE_ALPHABET = list("abcdefghijklmnopqrstuvwxyz")
# an enum if you squint
class actions:
    MOVE_N, MOVE_NE, MOVE_E, MOVE_SE, MOVE_S, MOVE_SW, MOVE_W, MOVE_NW, DESCEND = [i for i in range(9)]
    tile_move_actions = [MOVE_N, MOVE_NE, MOVE_E, MOVE_SE, MOVE_S, MOVE_SW, MOVE_W, MOVE_NW]

class directions:
    deltas =[[0, -1], [1, -1], [1, 0], [1, 1], [0, 1], [-1, 1], [-1, 0], [-1, -1]]

move_keybinds = {pygame.K_UP:actions.MOVE_N, pygame.K_DOWN:actions.MOVE_S,
                 pygame.K_LEFT:actions.MOVE_W, pygame.K_RIGHT:actions.MOVE_E,
                 pygame.K_w: actions.MOVE_N, pygame.K_s: actions.MOVE_S,
                 pygame.K_a: actions.MOVE_W, pygame.K_d: actions.MOVE_E,
                 pygame.K_q: actions.MOVE_NW, pygame.K_e: actions.MOVE_NE,
                 pygame.K_z: actions.MOVE_SW, pygame.K_c: actions.MOVE_SE,
                 pygame.K_GREATER:actions.DESCEND
                 }
def dist(p1, p2):
    return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** (1 / 2)


class tea_varieties:
    BLACK, GREEN, HERBAL, ENDGAME = range(4)
    colors = ((100, 100, 100), (100, 255, 100), (150, 0, 150), (255, 215, 0))
    names = ["black", "green", "herbal", "legendary"]

class effects:
    SPEEDY, HEALING, POISON, CONFUSION, RANDOM_DEBUG, \
        FARSIGHT, WARNING, ATK_BOOST, DEF_BOOST, MHP_UPGRADE, = range(10)
    special_effects = FARSIGHT, WARNING, ATK_BOOST, DEF_BOOST, MHP_UPGRADE
    names = "speedy", "healing", "poisoned", "confused", "random", \
                "farseeing", "paranoid", "hard-hitting", "sturdy", "invigorated"
    durations = 5, 2, 3, 3, 1, \
                    6, 6, 4, 4, 1


class factions:
    PLAYER, CAVE = range(2)

class Unit:
    def __init__(self, creature_name, proper_name, hp, maxhp, max_damage, char, x, y, parent_level, faction = factions.PLAYER, energy_regen=1):
        self.creature_name = creature_name
        self.proper_name = proper_name
        self.hp = hp
        self.maxhp = maxhp
        self.max_damage = max_damage
        self.char = char
        self.x, self.y = x, y
        self.view_range = 8
        self.max_inventory = 12
        self.inventory = []
        self.tea_deck = []
        self.max_tea_deck = 12
        self.memory = []
        self.faction = faction
        self.energy = 1
        self.energy_regen = energy_regen
        self.effects = {}
        self.living = True

        self.set_level(parent_level)
        self.tile = None


    def learn_coord(self, coord):
        if not coord in self.memory:
            self.memory.append(coord)

    def set_level(self, new_level, pos = None):
        self.parent_level = new_level
        new_level.place_unit(self, pos if pos else [self.x, self.y])

    def add_effect(self, effect, duration):
        if duration == 0: return
        if effect == effects.RANDOM_DEBUG:
            effect = random.choice(effects.special_effects)
        if not effect in self.effects:
            self.effects[effect] = duration
        else:
            self.effects[effect] += duration

    def process_effects(self):
        if self.faction == factions.PLAYER:
            pass
        elif self.faction == factions.CAVE:
            pass
        for effect in self.effects:
            self.effects[effect] -= 1
            if self.effects[effect] == 0:
                del self.effects[effect]

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
            if self.parent_level.valid_coords(newpos):
                # special check for kettle. this is gnarly and not in a good way
                # "I'll make stuff more organized by abstracting movement" <-- clueless
                if self.faction == factions.PLAYER and type(self.parent_level.get_tile(newpos).item)==Kettle:
                    kettle = self.parent_level.get_tile(newpos).item
                    kettle.bump(self)
                    return False

            if self.parent_level.get_tile(newpos).is_passable():
                newtile = self.parent_level.get_tile(newpos)
                if newtile.unit:
                    if newtile.unit.faction == self.faction and not effects.CONFUSION in self.effects:
                        return False
                    else:
                        self.attack(newtile.unit)
                        return True
                return self.move_to(newpos)
        if action == actions.DESCEND and self.faction == factions.PLAYER:
            if not self.tile.name == "stairs":
                self.parent_level.parent.add_message("There's no way down right here.")
                return False
            if not any(type(i)==Kettle for i in self.inventory):
                self.parent_level.parent.add_message("You daren't descend without your kettle.")
                return False
            self.parent_level.parent.enter_new_level()
            return False

    def get_name(self, article = True):
        name = self.proper_name if self.proper_name else self.creature_name
        return f"{'the ' if article and not self.proper_name else ''}{name}"

    def get_attack(self):
        return random.randint(0, self.max_damage) + (self.max_damage // 2 if effects.ATK_BOOST else 0)

    def get_defense(self):
        return 2 if effects.DEF_BOOST in self.effects else 0

    def attack(self, enemy):
        damage, fatal = 0, False
        damage = max(0, self.get_attack() - enemy.get_defense())
        enemy.hp -= damage
        if enemy.hp <= 0:
            enemy.die()
            fatal = True
        root = self.parent_level.parent
        root.add_message(f"{self.get_name().capitalize()} "
                         f"{'hit' if damage > 0 else 'missed'} {enemy.get_name()}"
                         f"{'!' if damage==self.max_damage else '.'}")
        if fatal: root.add_message(f"{enemy.get_name().capitalize()} dies!")
        return damage, fatal

    def die(self):
        self.living = False
        if self.inventory:
            self.drop(self.inventory[0])
        self.tile.clear_unit()

    def get_speed(self):
        return 1 if not effects.SPEEDY in self.effects else 1.5

    def add_item(self, item):
        if not item in self.inventory:
            self.inventory.append(item)

    def remove_item(self, item):
        if item in self.inventory:
            self.inventory.remove(item)

    def pick_up(self):
        if self.tile.item and len(self.inventory) < self.max_inventory:
            self.add_item(self.tile.item)
            self.tile.clear_item()
            return True
        return False

    def drop(self, item) -> bool:
        # tiles can only have one item, so this could fail
        if not self.tile.item:
            self.tile.item = item
            self.inventory.remove(item)
            if type(item)==Kettle: self.parent_level.parent.add_message("You set up the kettle. Pick it up after brewing.")
            return True
        return False

    def add_tea(self, tea):
        if len(self.tea_deck) < self.max_tea_deck:
            self.tea_deck.append(tea)
            return True
        return False

    def rendered(self):
        return FONT.render(self.char, False, [255, 255, 255], [0, 0, 0])

    def get_viewrange(self):
        return self.view_range

class Item:
    def __init__(self, name, char):
        self.name = name
        self.char = char
        self.tile = None

    def rendered(self) -> pygame.Surface:
        return FONT.render(self.char, False, [255, 255, 255], [0, 0, 0])

class TeaLeaf:
    def __init__(self, variety):
        self.name = tea_varieties.names[variety] + f" tea {'root' if variety==tea_varieties.HERBAL else 'leaf'}"
        self.char = "%"
        self.tile = None
        self.variety = variety
        self.color = tea_varieties.colors[self.variety]

    def rendered(self, color=None, bg_color=None) -> pygame.Surface:
        return FONT.render(self.char, True, color if color else self.color, bg_color)

class Tea:
    def __init__(self, variety):
        self.name = tea_varieties.names[variety] + " tea"
        self.char = "¶"
        self.tile = None
        self.variety = variety
        self.throw_effect = [None, effects.POISON, effects.CONFUSION][variety]
        self.quaff_effect = [effects.SPEEDY, effects.HEALING, effects.RANDOM_DEBUG][variety]
        self.color = tea_varieties.colors[self.variety]

    def rendered(self, color=None, bg_color=None) -> pygame.Surface:
        return FONT.render(self.char, True, color if color else self.color, bg_color)

class Kettle:
    def __init__(self, root):
        self.parent = root # kettle has to talk to the game root directly. probably unideal
        self.leaves = [        ]
        self.teas = []
        self.char, self.name = "ó", "kettle"
        self.color = (255-40, 215-40, 0)
        self.tile = None
        self.timer, self.prev_timer = 0, 0

    def bump(self, unit):
        if unit.faction != factions.PLAYER: return True
        if self.timer == 0 and not self.teas:
            self.activate()
        elif self.timer == 0 and self.teas:
            self.dispense_tea(unit)
        elif self.timer != 0:
            self.parent.add_message(f"{int(self.timer)} turns until tea is done.")
        return False
    def activate(self):
        self.parent.set_modal(BrewingWindow(self.parent, self))


    def dispense_tea(self, unit: Unit):
        [unit.add_tea(t) for t in self.teas]
        self.teas = []
        self.parent.set_modal(TeaDeckWindow(self.parent, self.teas, True))
        unit.inventory.append(self)
        self.parent.add_message("Picked up the kettle." if len(unit.inventory)<unit.max_inventory
                                else "You can barely stuff the kettle into your satchel.")
        self.tile.clear_item()

        pass

    def tick(self):
        if self.timer:
            self.prev_timer = self.timer
            self.timer -= 1 / self.parent.player.get_speed()
            if self.timer <= 0 and self.prev_timer > 0:
                self.parent.add_message("Done brewing!")
                for leaf in self.leaves:
                    self.teas.append(Tea(leaf.variety))
                self.timer = 0
                self.leaves = []

    def rendered(self, color=None, bg_color=None) -> pygame.Surface:
        if self.timer: color = (255, 215, 0)
        return FONT.render(self.char, True, color if color else self.color, bg_color)

class Tile:
    def __init__(self, char, passable, name, x, y, item=None, unit=None):
        self.char = char
        self.passable = passable
        self.name = name
        self.x, self.y = x, y
        self.item = item
        self.unit = unit

    def set_unit(self, unit):
        self.clear_unit()
        unit.tile = self
        unit.x, unit.y = self.x, self.y
        self.unit = unit

    def clear_unit(self):
        try:
            self.unit.tile = None
        except:pass
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
        return self.passable

    def rendered(self, color=[255, 255, 255], bg_color=[0,0,0]):
        if self.unit:
            return self.unit.rendered()
        elif self.item:
            return self.item.rendered()
        else:
            return FONT.render(self.char, False, color, bg_color)

class Level:
    def __init__(self, cols, rows, level_num):
        self.parent = None
        self.ncols = cols
        self.nrows = rows
        self.level_num = level_num
        self.tilemap = [[None for c in range(cols)] for r in range(rows)]

    def generate(self, floorgoal):
        self.tilemap = [[Tile("#", False, "wall", c, r) for c in range(self.ncols)] for r in range(self.nrows)]
        walkerx, walkery = self.ncols // 2, self.nrows // 2
        minx, miny, maxx, maxy = walkerx, walkery, walkerx, walkery
        floorcount = 0

        while floorcount < floorgoal:
            tile = self.get_tile([walkerx, walkery])
            if tile.name == "wall":
                self.set_tile(walkerx, walkery, Tile(".", True, "floor", walkerx, walkery))
                floorcount += 1
            if random.randint(0, 150) < 1:
                self.get_tile([walkerx, walkery]).set_item(TeaLeaf(tea_varieties.BLACK))
            walkerx = min(max(walkerx + random.choice([-1,-1, 0, 1, 1]), 0), self.ncols-2)
            walkery = min(max(walkery + random.choice([-1,0, 1]), 0), self.nrows - 2)
        self.set_tile(walkerx, walkery, Tile(">", True, "stairs", walkerx, walkery))
        start_candidates = [[c.x, c.y] for c in filter(lambda t: t.passable and dist([t.x, t.y], [walkerx, walkery])>10,
                                  self.all_tiles())]
        return random.choice(start_candidates) \
            if start_candidates \
            else [[c.x, c.y] for c in filter(lambda t: t.passable, self.all_tiles())]
        #print("generation done")

    def los_clear(self, from_coord, to_coord):
        line = bresenham(from_coord, to_coord)[1:-1]
        line = filter(lambda f: self.valid_coords(f), line)
        if all([self.get_tile(t).passable for t in line]):
            return True
    def place_unit(self, unit, pos):
        #print(f"placing {unit.name} at {pos}")
        tile = self.get_tile(pos)
        #print(f"tile at {pos} is {tile}")
        try:
            tile.set_unit(unit)
        except: pass

    def move_unit(self, unit, newpos) -> bool:
        # returns True on success, False on failure
        #print(f"moving to {newpos}")
        if not unit.parent_level == self:
            return False
        if not self.valid_coords(newpos):
            return False
        unit.tile.clear_unit()
        self.place_unit(unit, newpos)

        return True

    def valid_coords(self, coords):
        return (0 <= coords[0] < self.ncols) and \
               (0 <= coords[1] < self.nrows)

    def all_tiles(self):
        tiles = []
        for row in self.tilemap:
            for tile in row:
                tiles.append(tile)
        return tiles

    def by_faction(self, faction):
        return filter(lambda u: u.faction == faction,
                      [t.unit for t in list(filter(lambda t:t.unit,
                                  [t for t in self.all_tiles()]))])
    def render(self, surf):
        ppos = [self.parent.player.x, self.parent.player.y]
        nearby_tiles = filter(lambda t: dist([t.y, t.y], ppos) <= self.parent.player.get_viewrange(),
                              self.all_tiles())
        for row in self.tilemap:
            for tile in row:
                tpos = [tile.x, tile.y]
                #print(f"rendering tile at {tpos}")
                ppos = [self.parent.player.x, self.parent.player.y]
                if dist(tpos, ppos) <= self.parent.player.get_viewrange():
                    if self.los_clear(tpos, ppos):
                        rendered = tile.rendered()
                        player.learn_coord([tile.x, tile.y])
                        surf.blit(rendered, [tile.x*rendered.get_width(), tile.y*rendered.get_height()])
                    elif [tile.x, tile.y] in player.memory:
                        rendered = FONT.render(tile.char, False, [100, 100, 100])
                        surf.blit(rendered, [tile.x * rendered.get_width(), tile.y * rendered.get_height()])
                elif [tile.x, tile.y] in player.memory:
                    rendered = FONT.render(tile.char, False, [100, 100, 100])
                    surf.blit(rendered, [tile.x * rendered.get_width(), tile.y * rendered.get_height()])
                #rendered = tile.rendered()
                #surf.blit(rendered, [tile.x*rendered.get_width(), tile.y*rendered.get_height()])

    def get_tile(self, pos) -> [Optional[Tile]]:
        return self.tilemap[pos[1]][pos[0]]


    def set_tile(self, x, y, new_tile):
        try:
            self.tilemap[y][x] = new_tile
            return True
        except:
            return False

def get_subwindow_dimensions(percentage):
    surf_rect = pygame.Rect([0, 0, screen.get_width() * percentage, screen.get_height() * percentage])
    surf_rect.center = screen.get_rect().center
    surf = pygame.Surface([surf_rect.width, surf_rect.height])
    surf.fill([0, 0, 0])
    border_rect = pygame.Rect([0, 0, screen.get_width() * (percentage - 0.1), screen.get_height() * (percentage-0.1)])
    border_rect.center = surf.get_rect().center
    pygame.draw.rect(surf, [255, 255, 255], border_rect, 2, 2)
    return surf, border_rect

class GameRoot:
    def __init__(self, level: Level, player: Unit):
        self.level = level
        self.level.parent = self
        self.player = player
        self.active_modal = None
        self.active_kettle = None
        self.messages, self.message_log = [], []
        self.turns = 0

    def add_message(self, message):
        if not len(message) > (LEVEL_W-len("... --press any key--")):
            self.messages.append(message)
        else:
            lines = textwrap.wrap(message, LEVEL_W-len("...--press any key--"))
            for line in lines:
                self.messages.append(line+"...")

    def pop_message(self):
        self.message_log.append(self.messages.pop(0))

    def handle(self, ev:pygame.event.Event, delegate=True):
        if self.active_modal and delegate:
            self.active_modal.handle(ev)
        else:
            player_acted = False
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.KEYDOWN:
                #print(ev.key)
                if self.messages:
                    self.pop_message()
                    if len(self.messages) > 1: return
                elif len(self.messages) == 1:
                    self.pop_message()
                if ev.key in move_keybinds:
                    player_acted = self.player.act(move_keybinds[event.key])
                    if self.player.tile.item:
                        self.player.pick_up()
                if ev.key == pygame.K_i:
                    self.set_modal(InventoryWindow(self))
                if ev.key == pygame.K_g:
                    self.player.pick_up()
                if ev.key == pygame.K_PERIOD:
                    player_acted = True
            if ev.type == pygame.TEXTINPUT:
                if ev.text == "@":
                    self.set_modal(StatusWindow(self))
                elif ev.text == ">":
                    self.player.act(actions.DESCEND)
            if player_acted:
                self.advance()

    def advance(self):
        kettle = self.active_kettle
        if kettle:
            kettle.tick()
        monsters = self.level.by_faction(factions.CAVE)
        for monster in monsters:
            if monster.energy > 1:
                monster.act(random.choice(actions.tile_move_actions))
            monster.energy += (monster.energy_regen / player.get_speed())
        self.turns += 1

    def enter_new_level(self):
        new_level = Level(LEVEL_W, LEVEL_H, self.level.level_num+1 if self.level else 0)
        start = new_level.generate(LEVEL_FLOORCOUNT)
        self.player.set_level(new_level, start)
        self.player.memory = []
        new_level.parent = self
        self.level = new_level

    def render(self, surf:pygame.Surface):
        self.level.render(surf)
        if self.messages:
            surf.blit(FONT_MENUS.render(self.messages[0]+(" --press any key--" if len(self.messages) > 1 else ""), True, [255, 255, 255], [0,0,0]), [0,0])
        pl = self.player
        status_line = \
            f"{pl.proper_name}  {pl.hp}/{pl.maxhp}HP  " \
            f"Satchel: {len(pl.inventory)}/{pl.max_inventory} items  " \
            f"Cave layer {self.level.level_num}  " \
            f"Turn {self.turns}"
        surf.blit(FONT_MENUS.render(status_line, True, [255, 255, 255]), [0, HEIGHT-FONT_MENUS.get_height()-1])
        if self.active_modal:
            rendered:pygame.Surface = self.active_modal.rendered()
            centered_rect = rendered.get_rect()
            centered_rect.center = surf.get_rect().center
            surf.blit(rendered, centered_rect)

    def set_kettle(self, kettle):
        self.active_kettle = kettle

    def set_modal(self, modal):
        self.active_modal = modal
        self.active_modal.parent = self

    def clear_modal(self):
        self.active_modal.parent = None
        self.active_modal = None

class StatusWindow:
    def __init__(self, parent:GameRoot):
        self.parent = parent

    def rendered(self) -> pygame.Surface:
        return pygame.Surface([10, 10])

    def handle(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == RCLICK:
            self.close()
        elif ev.type == pygame.QUIT:
            self.parent.handle(ev, delegate=False)

    def close(self):
        self.parent.clear_modal()

class InventoryWindow:
    def __init__(self, parent:GameRoot):
        self.parent = parent

    def rendered(self) -> pygame.Surface:
        antialias_menu = True
        surf_rect = pygame.Rect([0,0,screen.get_width()*0.8, screen.get_height()*0.8])
        surf_rect.center = screen.get_rect().center
        surf = pygame.Surface([surf_rect.width, surf_rect.height])
        surf.fill([0,0,0])
        border_rect = pygame.Rect([0,0,screen.get_width()*0.79, screen.get_height()*0.79])
        border_rect.center = surf.get_rect().center
        pygame.draw.rect(surf, [255, 255, 255], border_rect, 2, 2)
        title_rendered = FONT_MENUS.render("Your Satchel", antialias_menu, [255, 255, 255])

        names = [i.name for i in self.parent.player.inventory]
        name_blits = []

        for i in range(len(names)):

            name = names[i]
            x = border_rect.centerx - (120)*(1,-1)[i>5] - 50
            y = border_rect.top + 30*((i) % 6) + 25
            surf.blit(FONT_MENUS.render(name, antialias_menu, [255, 255, 255]),[x, y])
            surf.blit(self.parent.player.inventory[i].rendered(), [x-20, y])
            surf.blit(FONT_MENUS.render(THE_ALPHABET[i], True, [255, 255, 255]),
                      [x - 50, y])

            #print(f"blitted item {i} at {x, y}")

        instr = FONT_MENUS.render("press letter to drop item", antialias_menu, (255, 255, 255))
        surf.blit(instr,
                  [border_rect.centerx - instr.get_width() // 2, border_rect.bottom - 1.5 * FONT_MENUS.get_height()])
        surf.blit(title_rendered, [border_rect.centerx-title_rendered.get_width()//2, border_rect.y+10])
        return surf

    def handle(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == RCLICK:
            self.close()
        elif ev.type == pygame.QUIT:
            self.parent.handle(ev, delegate=False)
        elif ev.type == pygame.TEXTINPUT:
            key = ev.text
            i = THE_ALPHABET.index(key)
            if i<len(self.parent.player.inventory):
                item = self.parent.player.inventory[i]
                if self.parent.player.drop(item):
                    self.close()



    def close(self):
        self.parent.clear_modal()

class BrewingWindow:
    def __init__(self, parent: GameRoot, kettle:Kettle):
        self.parent = parent
        self.kettle = kettle

        self.satchel_contents =list(filter(lambda i: type(i)==TeaLeaf,
            parent.player.inventory))
        self.kettle_contents = []
        self.tab = 0
        self.selected = 0


    def rendered(self):
        antialias_menu = True
        surf, border_rect = get_subwindow_dimensions(0.8)
        pygame.draw.line(surf, [255, 255, 255], [border_rect.centerx, border_rect.top + 30], [border_rect.centerx, border_rect.bottom - 30], 2)
        title_rendered = FONT_MENUS.render("Filling the Kettle", antialias_menu, [255, 255, 255])
        satchel_label = FONT_MENUS.render("Satchel", antialias_menu, [255, 255, 255])
        kettle_label = FONT_MENUS.render("Kettle", antialias_menu, [255, 255, 255])
        surf.blit(title_rendered, [border_rect.centerx - title_rendered.get_width() // 2, border_rect.y + 10])
        surf.blit(satchel_label, [border_rect.width // 4 - kettle_label.get_width() // 2, border_rect.y + 2.5*FONT_MENUS.get_height()])
        surf.blit(kettle_label, [border_rect.width * (3/4) - kettle_label.get_width() // 2,
                                  border_rect.y + 2.5 * FONT_MENUS.get_height()])
        # almost stupidest way to do this
        # I had a stupider way
        tvs = [tea_varieties.BLACK, tea_varieties.GREEN, tea_varieties.HERBAL, tea_varieties.ENDGAME]
        s_counts = []
        for tv in tvs:
            s_counts.append(len(list(filter(lambda i: i.variety==tv, self.satchel_contents))))
        k_counts = []
        for tv in tvs:
            k_counts.append(len(list(filter(lambda i: i.variety==tv, self.kettle_contents))))
        labels = list("abcd") # I can hardcode the alphabet; not like it's gonna change, right
        for i in range(4):
            satchel_render = FONT_MENUS.render(f"{labels[i]} - {s_counts[i]}x {tea_varieties.names[tvs[i]]}", antialias_menu, [255, 255, 255] if self.tab==0 else [150, 150, 150])
            kettle_render = FONT_MENUS.render(f"{labels[i]} - {k_counts[i]}x {tea_varieties.names[tvs[i]]}", antialias_menu, [255, 255, 255] if self.tab==1 else [150, 150, 150])
            surf.blit(satchel_render,
                      [border_rect.width // 4 - satchel_render.get_width() // 2, border_rect.y + ((i*1.5)+5)*FONT_MENUS.get_height()])
            surf.blit(kettle_render,
                      [border_rect.width * (3/4) - kettle_render.get_width() // 2,
                       border_rect.y + ((i * 1.5) + 5) * FONT_MENUS.get_height()])
        instr = FONT_MENUS.render("[tab] switches tabs", antialias_menu, (255, 255, 255))
        surf.blit(instr,
                  [border_rect.centerx-instr.get_width()//2, border_rect.bottom-1.5*FONT_MENUS.get_height()])
        return surf

    def handle(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == RCLICK:
            self.close()
        elif ev.type == pygame.QUIT:
            self.parent.handle(ev, delegate=False)
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_TAB:
                self.tab = [1, 0][self.tab]
        if ev.type == pygame.TEXTINPUT:
            if ev.text in list("abcd"):
                container = [self.satchel_contents, self.kettle_contents][self.tab]
                leaves = list(filter(lambda l: l.variety==list("abcd").index(ev.text),
                                   container))
                if leaves: leaf = leaves[0]
                else: return

                if self.tab == 0:
                    if not kettle.leaves or (len(self.kettle.leaves) > 0 and self.kettle.leaves[0].variety == leaf.variety):
                        self.parent.player.inventory.remove(leaf)
                        self.kettle.leaves.append(leaf)
                else:
                    self.kettle.leaves.remove(leaf)
                    self.parent.player.inventory.append(leaf)
                self.satchel_contents = list(filter(lambda i: type(i) == TeaLeaf,
                                                    self.parent.player.inventory))
                self.kettle_contents = kettle.leaves

    def close(self):
        self.kettle.timer = int(1.5*len(self.kettle.leaves))
        if self.kettle.timer: self.parent.add_message(f"Started a kettle of {tea_varieties.names[self.kettle.leaves[0].variety]} tea.")
        self.parent.clear_modal()

class TeaDeckWindow:
    def __init__(self, parent:GameRoot, new_teas, rearrange=False):
        self.parent = parent
        self.new_teas = new_teas
        self.rearrange = rearrange

    def handle(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == RCLICK:
            self.close()
        elif ev.type == pygame.QUIT:
            self.parent.handle(ev, delegate=False)
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_TAB:
                self.tab = [1, 0][self.tab]

    def rendered(self):
        pl = self.parent.player
        surf, border_rect = get_subwindow_dimensions(0.8)
        y = border_rect.top + 1.5*FONT_MENUS.get_height()
        for tea in pl.tea_deck:
            tea_desc = FONT_MENUS.render(tea.name, True, [255, 255, 255])
            tea_char = tea.rendered()
            x=border_rect.centerx-tea_desc.get_width()//2
            surf.blit(tea_desc, [x, y])
            surf.blit(tea_char, [x-20, y])
        return surf

    def close(self):
        self.parent.clear_modal()




lev = Level(LEVEL_W, LEVEL_H, 1)
start = lev.generate(int((72*20)*0.3))

player = Unit("questant", "Tom", 10, 10, 4, "@", *start, lev)
mob =    Unit("goblin", "", 5, 5, 3, "g", player.x+1, player.y+1, lev, factions.CAVE)


tealeaf = TeaLeaf(tea_varieties.HERBAL)
tealeaf2 = TeaLeaf(tea_varieties.BLACK)
[player.inventory.append(tealeaf) for i in range(5)]
player.inventory.append(tealeaf2)

player.set_level(lev, [player.x, player.y])
mob.set_level(lev, [player.x+1, player.y+1])

game = GameRoot(lev, player)



game.add_message("Welcome to TeaRL! '?' for help.")

ktile = lev.get_tile([player.x, player.y-1])
kettle = Kettle(game)
ktile.set_item(kettle)
game.set_kettle(kettle)

#kettle.activate()

clock = pygame.time.Clock()


while True:
    for event in pygame.event.get():
        game.handle(event)
    screen.fill([0,0,0])
    game.render(screen)

    pygame.display.flip()
    #player.move_to([player.x + 1, player.y])
    clock.tick(60)



