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

Room = collections.namedtuple('Room', 'x y width height')
Point = collections.namedtuple('Point', 'x y')

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


def create_path(level, p0, p1):
    '''
    Connect two points on the map with a path.
    '''
    # Compute all possible directions from here
    points = []
    for (dx, dy) in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        p = Point(p0.x+dx, p0.y+dy)
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


def add_staircase(level, room, staircase):
    '''
    Add staircase to random location within the room
    '''
    points = []

    for j in range(1, room.height):
        for i in range(1, room.width):
            points.append(Point(room.x+i, room.y+j))

    p = random.choice(points)
    level[p.x][p.y] = staircase


def make_level():
    '''
    Create a X_DIM by Y_DIM 2-D list filled with a random assortment of rooms.
    '''
    level = []
    for i in range(X_DIM):
        level.append([None] * Y_DIM)

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
    add_staircase(level, up, '<')
    add_staircase(level, down, '>')

    return level


def find_staircase(level, staircase):
    '''
    Scan the level to determine where a particular staircase is
    '''
    for j in range(Y_DIM):
        for i in range(X_DIM):
            if level[i][j] == staircase:
                return Point(i, j)
    return None


def print_level(level):
    '''
    Print the level using spaces when a tile isn't set
    '''
    for j in range(Y_DIM):
        for i in range(X_DIM):
            if level[i][j] == None:
                sys.stdout.write(' ')
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
    current = 0
    levels.append(make_level())

    pos = find_staircase(levels[current], '<')

    while True:
        # Clear the terminal
        sys.stdout.write("\x1b[2J\x1b[H")

        level = levels[current]

        # Swap in an '@' character in the position of the character, print the
        # level, and then swap back
        old, level[pos.x][pos.y] = level[pos.x][pos.y], '@'
        print_level(level)
        level[pos.x][pos.y] = old

        key = read_key()

        if key == 'q':
            break
        elif key == 'h':
            newpos = Point(pos.x-1, pos.y)
        elif key == 'j':
            newpos = Point(pos.x, pos.y+1)
        elif key == 'k':
            newpos = Point(pos.x, pos.y-1)
        elif key == 'l':
            newpos = Point(pos.x+1, pos.y)
        else:
            continue

        if level[newpos.x][newpos.y] == '>':
            # Moving down a level
            if current == len(levels) - 1:
                levels.append(make_level())
            current += 1
            newpos = find_staircase(levels[current], '<')
        elif level[newpos.x][newpos.y] == '<':
            # Moving up a level
            if current > 0:
                current -= 1
                newpos = find_staircase(levels[current], '>')
        elif level[newpos.x][newpos.y] not in ['.', '+', '#']:
            # Hit a wall, should stay put
            newpos = pos

        pos = newpos
