import datetime
import itertools
import random


SHAPES = [0, 1, 2]
COLORS = [0, 1, 2]
SHADINGS = [0, 1, 2]
NUMBERS = [1, 2, 3]


def all_cards():
    # represent each card as a tuple (shape, color, shading, number)
    return [(s, c, sh, n) for s, c, sh, n in itertools.product(SHAPES, COLORS, SHADINGS, NUMBERS)]


def is_set(a, b, c):
    # for each property, either all same or all different
    for i in range(4):
        vals = {a[i], b[i], c[i]}
        if len(vals) == 2:
            return False
    return True


def find_sets(board):
    sets = []
    for a, b, c in itertools.combinations(board, 3):
        if is_set(a, b, c):
            sets.append((a, b, c))
    return sets


def today_str():
    return datetime.date.today().isoformat()


def daily_board(date: str = "", size: int = 12):
    date = date or today_str()
    # deterministic seed from date
    seed = int(''.join([c for c in date if c.isdigit()]))
    rng = random.Random(seed)
    deck = all_cards()
    rng.shuffle(deck)
    board = deck[:size]
    # ensure at least one set present; if not, reshuffle a few times
    for _ in range(10):
        if find_sets(board):
            break
        rng.shuffle(deck)
        board = deck[:size]
    return [list(card) for card in board]
