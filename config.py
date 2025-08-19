"""Game wide configuration constants.

The original project kept a number of values spread across modules.  For the
reworked version the majority of tweakable numbers live in this file so that
balancing the prototype is easier.  Only very small gameplay slices are
implemented in this kata, the large list mainly mirrors the specification in
the user prompt.
"""

# --- World ---------------------------------------------------------------

# The playable world is intentionally huge.  A camera/viewport will follow the
# player around this space while the bots use grid based path finding.
WIDTH, HEIGHT = 9000, 9000
VIEW_W, VIEW_H = 1280, 720
GRID = 32
COLS, ROWS = WIDTH // GRID, HEIGHT // GRID
FPS = 60

# --- Movement -----------------------------------------------------------

RADIUS = 16
PLAYER_SPEED = 3.3
BOT_SPEED = 3.1
LOW_HP_SPEED = 1.6

SEP_RADIUS = 60
SEP_STRENGTH = 1.1
STUCK_MS = 600
RESERVE_MS = 200

# --- Combat -------------------------------------------------------------

BULLET_SPEED = 7.5
BULLET_RADIUS = 5

MAX_HP = 100
LOW_HP_THRESH = 28

FOV_DEGREES = 100
FOV_RANGE = 560
HEARING_RADIUS = 420

# --- Bomb rules ---------------------------------------------------------

PLANT_MS = 5_000
DEFUSE_MS = 10_000
BOMB_TIMER_MS = 30_000
REVIVE_MS = 10_000
BLEEDOUT_MS = 5_000
REVIVE_RANGE = 70
BOMB_RADIUS_MIN = 7
BOMB_RADIUS_MAX = 9

# --- Economy ------------------------------------------------------------

ECON = {"win": 3000, "loss": 2000, "plant": 300}

# Weapon/utility data used by the buy menu and entity logic.  Only a subset of
# the values are used in the simplified implementation.
WEAPONS = {
    "Classic":   {"price": 0,    "dmg": 26,  "rof_ms": 180, "mag": 12},
    "Sheriff":   {"price": 800,  "dmg": 55,  "rof_ms": 350, "mag": 6},
    "Stinger":   {"price": 950,  "dmg": 24,  "rof_ms": 90,  "mag": 20},
    "Spectre":   {"price": 1600, "dmg": 26,  "rof_ms": 110, "mag": 30},
    "Bulldog":   {"price": 2050, "dmg": 34,  "rof_ms": 140, "mag": 24},
    "Phantom":   {"price": 2900, "dmg": 39,  "rof_ms": 120, "mag": 30},
    "Vandal":    {"price": 2900, "dmg": 40,  "rof_ms": 140, "mag": 30},
    "Operator":  {"price": 4700, "dmg": 150, "rof_ms": 900, "mag": 5},
    "Judge":     {"price": 1850, "dmg": 12,  "rof_ms": 110, "mag": 7},
    "Marshal":   {"price": 1100, "dmg": 101, "rof_ms": 600, "mag": 5},
}

ARMORS = {
    "Light": {"price": 400, "dr": 0.20},
    "Heavy": {"price": 1000, "dr": 0.35},
}

UTILS = {
    "Smoke": {"price": 200},
    "Flash": {"price": 250},
    "Wall":  {"price": 400},
}

# --- Minimap ------------------------------------------------------------

MINIMAP_SIZE = 260
ENEMY_MEMORY_MS = 2_000

# --- Colours ------------------------------------------------------------

WHITE = (255, 255, 255)
GRID_DARK = (30, 30, 32)
GRID_LINE = (36, 36, 38)
WALL_DARK = (74, 76, 84)
WALL_EDGE = (130, 130, 140)
BLUE = (40, 150, 255)
RED = (235, 60, 60)
GREEN = (70, 200, 100)
YELLOW = (250, 210, 70)
CYAN = (60, 220, 220)
ORANGE = (255, 150, 60)
GREY = (170, 170, 170)
BLUE_BOT = (110, 185, 255)
RED_BOT = (255, 135, 135)
