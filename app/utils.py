"""Utility functions for the MoodFlix app."""

from datetime import date


def compute_age(date_of_birth: date) -> int:
    """
    Compute age in years from date_of_birth to today.

    Args:
        date_of_birth: The user's date of birth.

    Returns:
        Age in full years.
    """
    today = date.today()
    age = today.year - date_of_birth.year
    if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
        age -= 1
    return age
