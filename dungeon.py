#! /usr/bin/env python3

import collections
import copy
import random
import sys
import termios
import tty

# Dimensions of the dungeon
X_DIM = 80
Y_DIM = 20

# Min and Max number of rooms per floor
NUM_ROOMS = (3, 5)

# Min and Max height and width of a room
ROOM_HEIGHT = (5, 8)
ROOM_WIDTH = (5, 20)

# Minimum separation between rooms
MIN_SEP = 2

TRAP_PROB = 0.5

MONSTER_PROB = 0.9

REGEN_PROB = 0.05 # 1/20 chance

MOVEABLE = ['.', '+', '#', '>', '<']

Room = collections.namedtuple('Room', 'x y width height')
Point = collections.namedtuple('Point', 'x y')

MONSTERS = [
    ('kiwi', 'k', 2, 1),
    ('goblin', 'g', 10, 1),
    ('panda', 'P', 40, 1),
]

class Monster:
    def __init__(self, pos, name, what, hp, dmg):
        self.pos = pos
        self.name = name
        self.what = what
        self.hp = hp
        self.dmg = dmg
        self.old = '.' # monsters always spawn on a '.'

    def move(self, level, newpos):
        level[self.pos.x][self.pos.y] = self.old
        self.old = level[newpos.x][newpos.y]
        level[newpos.x][newpos.y] = 'm'
        self.pos = newpos

    def die(self, level):
        level[self.pos.x][self.pos.y] = self.old


def random_door(level, room):
    '''
    Picks a random side for a door in and out of a room.
    '''
    deltax = deltay = 0

    # Pick random side on room
    side = random.randint(0, 3)
    if side == 0 or side == 2:
        deltay = random.randint(1, room.height-1)
    elif side == 1 or side == 3:
        deltax = random.randint(1, room.width-1)

    if side == 1:
        deltay = room.height
    elif side == 2:
        deltax = room.width

    return Point(room.x + deltax, room.y + deltay)


def fill_room(level, room):
    '''
    Fill in a new room in the level, drawing borders around the room and
    periods inside the room. Returns a copy of the level with the new room
    added if the room did not collide with an existing room. Returns None if
    there was a collision.
    '''
    new_level = copy.deepcopy(level)

    # Populate new_level with room
    for j in range(room.height+1):
        for i in range(room.width+1):
            # Check if there's already a room here
            if level[room.x+i][room.y+j] != None:
                return None

            if j == 0 or j == room.height:
                new_level[room.x+i][room.y+j] = '-'
            elif i == 0 or i == room.width:
                new_level[room.x+i][room.y+j] = '|'
            else:
                new_level[room.x+i][room.y+j] = '.'

    # Ensure MIN_SEP space exists to left and right
    for j in range(room.height+1):
        if level[room.x-MIN_SEP][room.y+j] != None:
            return None
        if level[room.x+room.width+MIN_SEP][room.y+j] != None:
            return None

    # Ensure MIN_SEP space exists above and below
    for i in range(room.width+1):
        if level[room.x+i][room.y-MIN_SEP] != None:
            return None
        if level[room.x+i][room.y+room.height+MIN_SEP] != None:
            return None

    return new_level


def dist(p0, p1):
    '''
    Compute the euclidean distance between two points
    '''
    return ((p0.x - p1.x)**2 + (p0.y - p1.y)**2)**0.5


def dxdy(p):
    '''
    Yield the locations around the position to the left, right, above, and
    below.
    '''
    for (dx, dy) in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        yield Point(p.x+dx, p.y+dy)


def create_path(level, p0, p1):
    '''
    Connect two points on the map with a path.
    '''
    # Compute all possible directions from here
    points = []
    for p in dxdy(p0):
        if p == p1:
            return True

        if p.x >= X_DIM or p.x < 0:
            continue
        if p.y >= Y_DIM or p.y < 0:
            continue
        if level[p.x][p.y] not in [None, '#']:
            continue

        points.append(p)

    # Sort points according to distance from p1
    points.sort(key=lambda i: dist(i, p1))

    for p in points:
        old, level[p.x][p.y] = level[p.x][p.y], '$'
        if create_path(level, p, p1):
            level[p.x][p.y] = '#'
            return True
        level[p.x][p.y] = old

    return False


def add_to_room(level, room, what):
    '''
    Pick a random open location in the room and add what at the location.
    '''
    points = []

    for j in range(1, room.height):
        for i in range(1, room.width):
            if level[room.x+i][room.y+j] == '.':
                points.append(Point(room.x+i, room.y+j))

    if len(points) == 0:
        return None

    p = random.choice(points)
    level[p.x][p.y] = what
    return p


def make_level():
    '''
    Create a X_DIM by Y_DIM 2-D list filled with a random assortment of rooms.
    '''
    level = []
    for i in range(X_DIM):
        level.append([None] * Y_DIM)

    monsters = []
    rooms = []

    # Randomly N generate room in level
    for i in range(random.randint(*NUM_ROOMS)):
        # Keep looking, there should be *somewhere* to put this room...
        while True:
            # Generate random room
            x = random.randint(MIN_SEP, X_DIM)
            y = random.randint(MIN_SEP, Y_DIM)
            height = random.randint(*ROOM_HEIGHT)
            width = random.randint(*ROOM_WIDTH)

            # Check map boundary
            if x + width + MIN_SEP >= X_DIM:
                continue
            if y + height + MIN_SEP >= Y_DIM:
                continue

            room = Room(x, y, width, height)
            new_level = fill_room(level, room)

            if not new_level:
                continue

            level = new_level
            rooms.append(room)

            # Check whether we should add a trap to this room
            if random.random() < TRAP_PROB:
                add_to_room(level, room, 'x')

            # Check whether we should add a monster to this room
            if random.random() < MONSTER_PROB:
                p = add_to_room(level, room, 'm')
                if p:
                    m = MONSTERS[random.randrange(len(MONSTERS))]
                    monsters.append(Monster(p, *m))

            break

    # Connect the rooms with random paths
    for i in range(len(rooms)-1):
        # Pick two random doors
        door0 = random_door(level, rooms[i])
        door1 = random_door(level, rooms[i+1])

        level[door0.x][door0.y] = '+'
        level[door1.x][door1.y] = '+'

        # Actually connect them
        if not create_path(level, door0, door1):
            # TODO: Could happen... what should we do?
            pass

    # Pick random room for stairs leading up and down
    up, down = random.sample(rooms, 2)
    add_to_room(level, up, '<')
    add_to_room(level, down, '>')

    return level, monsters


def find_staircase(level, staircase):
    '''
    Scan the level to determine where a particular staircase is
    '''
    for j in range(Y_DIM):
        for i in range(X_DIM):
            if level[i][j] == staircase:
                return Point(i, j)
    return None


def print_level(level, monsters):
    '''
    Print the level using spaces when a tile isn't set
    '''
    for j in range(Y_DIM):
        for i in range(X_DIM):
            if level[i][j] == None:
                sys.stdout.write(' ')
            elif level[i][j] == 'x':
                # It's a trap!
                sys.stdout.write('.')
            elif level[i][j] == 'm':
                for m in monsters:
                    if m.pos.x == i and m.pos.y == j:
                        sys.stdout.write(m.what)
                        break
            else:
                sys.stdout.write(level[i][j])
        sys.stdout.write('\n')


def read_key():
    '''
    Read a single key from stdin
    '''
    try:
        fd = sys.stdin.fileno()
        tty_settings = termios.tcgetattr(fd)
        tty.setraw(fd)

        key = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, tty_settings)
    return key


if __name__ == '__main__':
    # Initialize the first level
    levels = []
    monsters = []

    current = 0

    res = make_level()
    levels.append(res[0])
    monsters.append(res[1])

    pos = find_staircase(levels[current], '<')

    curhp = maxhp = 10

    while True:
        wait = False

        # Clear the terminal
        sys.stdout.write("\x1b[2J\x1b[H")

        if curhp <= 0:
            sys.stdout.write('You died. gg\n')
            break

        level = levels[current]

        # Swap in an '@' character in the position of the character, print the
        # level, and then swap back
        old, level[pos.x][pos.y] = level[pos.x][pos.y], '@'
        print_level(level, monsters[current])
        level[pos.x][pos.y] = old

        sys.stdout.write('Health: {}/{}\n'.format(curhp, maxhp))

        key = read_key()

        if key == 'q':
            break
        elif key == '.':
            newpos = pos
        elif key == 'h':
            newpos = Point(pos.x-1, pos.y)
        elif key == 'j':
            newpos = Point(pos.x, pos.y+1)
        elif key == 'k':
            newpos = Point(pos.x, pos.y-1)
        elif key == 'l':
            newpos = Point(pos.x+1, pos.y)
        elif key == '>':
            if level[newpos.x][newpos.y] == '>':
                # Moving down a level
                if current == len(levels) - 1:
                    res = make_level()
                    levels.append(res[0])
                    monsters.append(res[1])

                current += 1
                pos = find_staircase(levels[current], '<')
                continue
        elif key == '<':
            if level[newpos.x][newpos.y] == '<':
                # Moving up a level
                if current > 0:
                    current -= 1
                    pos = find_staircase(levels[current], '>')
                    continue
        else:
            continue

        if level[newpos.x][newpos.y] in ['x', 'o']:
            # Walked onto a trap, reveal the trap and hurt the player
            level[newpos.x][newpos.y] = 'o'
            curhp -= 1
            wait = False
            sys.stdout.write('Ouch, it\' a trap!\n')
        elif level[newpos.x][newpos.y] == 'm':
            # Walked into a monster, attack!
            for m in monsters[current]:
               if m.pos == newpos:
                    m.hp -= 2
            newpos = pos
        elif level[newpos.x][newpos.y] not in MOVEABLE:
            # Hit a wall, should stay put
            newpos = pos

        pos = newpos

        # Random chance to regen some health
        if random.random() < REGEN_PROB:
            curhp += 1
            curhp = min(curhp, maxhp)

        # Update the monsters
        for m in monsters[current]:
            if m.hp <= 0:
                m.die(level)
                monsters[current].remove(m)
                sys.stdout.write('You\'ve done it, you killed a {}!\n'.format(m.name))
                wait = True
                continue

            d0 = dist(pos, m.pos)
            if d0 < 15:
                # Move the monster towards the player
                for p in dxdy(m.pos):
                    d1 = dist(pos, p)
                    if pos == p:
                        # Monster moves into player, attack!
                        curhp -= m.dmg
                    elif level[p.x][p.y] in MOVEABLE and d1 < d0:
                        m.move(level, p)
                        break

        # See if we should wait before redrawing the level
        if wait:
            sys.stdout.flush()
            key = read_key()
