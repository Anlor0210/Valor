"""User interface helpers.

The functions are intentionally light‑weight; the goal is to provide a simple
minimap and a basic buy menu that are good enough for unit testing.  The real
project referenced in the prompt would contain a far more feature rich system.
"""

from __future__ import annotations

import pygame
from typing import Sequence

from config import (
    WIDTH,
    HEIGHT,
    GRID,
    MINIMAP_SIZE,
    ENEMY_MEMORY_MS,
    WHITE,
    GREY,
    WEAPONS,
)


# ---------------------------------------------------------------------------
# Minimap
# ---------------------------------------------------------------------------

def draw_minimap(surface: pygame.Surface, player, walls, bomb, agents: Sequence) -> None:
    """Draw a very small representation of the arena in the top right."""

    scale = MINIMAP_SIZE / WIDTH
    mini = pygame.Surface((MINIMAP_SIZE, MINIMAP_SIZE), pygame.SRCALPHA)
    mini.fill((20, 20, 24))

    for w in walls:
        pygame.draw.rect(
            mini,
            (100, 100, 100),
            pygame.Rect(int(w.x * scale), int(w.y * scale), int(w.w * scale), int(w.h * scale)),
        )

    pygame.draw.circle(
        mini,
        (80, 80, 120),
        (int(bomb.zone_center[0] * scale), int(bomb.zone_center[1] * scale)),
        int(bomb.radius * scale * GRID),
        1,
    )

    now = pygame.time.get_ticks()
    for ag in agents:
        if ag.team == player.team:
            pygame.draw.circle(mini, ag.color, (int(ag.x * scale), int(ag.y * scale)), 3)
        else:
            seen_time = ag.seen_by_att if player.team == "ATT" else ag.seen_by_def
            elapsed = now - seen_time
            if elapsed < ENEMY_MEMORY_MS:
                alpha = max(50, 255 - int(255 * elapsed / ENEMY_MEMORY_MS))
                dot = pygame.Surface((6, 6), pygame.SRCALPHA)
                pygame.draw.circle(dot, (*ag.color, alpha), (3, 3), 3)
                mini.blit(dot, (int(ag.x * scale) - 3, int(ag.y * scale) - 3))

    surface.blit(mini, (surface.get_width() - MINIMAP_SIZE - 20, 20))


# ---------------------------------------------------------------------------
# Buy menu
# ---------------------------------------------------------------------------

def draw_buy_menu(surface: pygame.Surface, agent) -> None:
    """Render a very small textual buy menu in the centre of ``surface``."""

    font = pygame.font.SysFont("consolas", 18)
    panel = pygame.Surface((360, 260))
    panel.fill((16, 16, 18))
    pygame.draw.rect(panel, (60, 60, 60), panel.get_rect(), 2)

    for i, (name, data) in enumerate(WEAPONS.items(), start=1):
        price = data["price"]
        text = f"{i}. {name} [{price}]"
        colour = WHITE if agent.credits >= price else GREY
        panel.blit(font.render(text, True, colour), (12, 12 + (i - 1) * 22))

    surface.blit(panel, (surface.get_width() // 2 - 180, surface.get_height() // 2 - 130))


# ---------------------------------------------------------------------------
# HUD helper
# ---------------------------------------------------------------------------

def draw_hud(surface: pygame.Surface, agent) -> None:
    font = pygame.font.SysFont("consolas", 16)
    text = font.render(f"Credits: {agent.credits}", True, WHITE)
    surface.blit(text, (16, 40))
