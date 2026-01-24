"""
In-memory user data store.

This module is responsible for managing simple user-related data
such as the watchlist. It is designed to be replaced by a database
layer in the future.
"""

from typing import List, Set


# In-memory storage for saved show titles (single anonymous user)
_watchlist: Set[str] = set()


def add_to_watchlist(title: str) -> None:
    """
    Add a show title to the watchlist.
    """
    _watchlist.add(title)


def remove_from_watchlist(title: str) -> None:
    """
    Remove a show title from the watchlist.
    """
    _watchlist.discard(title)


def get_watchlist() -> List[str]:
    """
    Return all saved show titles.
    """
    return sorted(_watchlist)
