from __future__ import annotations

"""Very small economy / buy phase helpers.

This module is intentionally tiny – enough to showcase the structure used by the
full project.  The data tables for weapons/armour live in ``config`` while these
functions manipulate ``Agent`` instances.
"""

from typing import Iterable
import pygame

from config import WEAPONS, ARMORS, UTILS


def start_buy_phase(agents: Iterable, team: str, duration_ms: int = 9000) -> int:
    """Enable purchasing for ``agents`` for ``duration_ms`` milliseconds.

    Returns the timestamp when the phase ends.
    """

    end_time = pygame.time.get_ticks() + duration_ms
    for a in agents:
        a.buy_time_end = end_time
    return end_time


def _price_of(item_name: str) -> int:
    if item_name in WEAPONS:
        return WEAPONS[item_name]["price"]
    if item_name in ARMORS:
        return ARMORS[item_name]["price"]
    if item_name in UTILS:
        return UTILS[item_name]["price"]
    raise KeyError(item_name)


def can_buy(agent, item_name: str) -> bool:
    now = pygame.time.get_ticks()
    price = _price_of(item_name)
    return getattr(agent, "buy_time_end", 0) > now and agent.credits >= price


def buy(agent, item_name: str) -> bool:
    if not can_buy(agent, item_name):
        return False
    price = _price_of(item_name)
    agent.credits -= price
    agent.equip(item_name)
    return True
