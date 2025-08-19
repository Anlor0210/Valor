import math
import pygame
from config import GRID, BOMB_TIMER_MS


def load_sprites():
    """Load optional sprites used by the game."""
    sprites = {}
    try:
        sprites["bomb"] = pygame.image.load("assets/bomb.png").convert_alpha()
    except Exception:
        sprites["bomb"] = None
    return sprites


def draw_bomb(surface, bomb_state, sprites, cam=(0, 0)):
    """Draw the bomb icon or a fallback circle at the bomb's zone.

    If a bomb sprite is supplied in ``sprites['bomb']`` it will be blitted
    centered at the bomb location.  Otherwise a simple circle is used.  When
    the bomb is planted a small countdown ring indicates the remaining time
    until detonation.
    """
    pos = (
        int(bomb_state.zone_center[0] - cam[0]),
        int(bomb_state.zone_center[1] - cam[1]),
    )
    icon = sprites.get("bomb")
    if icon:
        rect = icon.get_rect(center=pos)
        surface.blit(icon, rect)
    else:
        pygame.draw.circle(surface, (120, 120, 160), pos, 8)

    if bomb_state.state == "planted":
        elapsed = pygame.time.get_ticks() - bomb_state.planted_time
        remaining = max(0, BOMB_TIMER_MS - elapsed)
        frac = remaining / BOMB_TIMER_MS if BOMB_TIMER_MS else 0
        radius = 16
        rect = pygame.Rect(0, 0, radius * 2, radius * 2)
        rect.center = pos
        start_angle = -math.pi / 2
        end_angle = start_angle + 2 * math.pi * frac
        pygame.draw.arc(surface, (255, 60, 60), rect, start_angle, end_angle, 3)
