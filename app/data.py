# Static TV show dataset for MVP portfolio project.
# Data only — no logic, no filtering, no user input handling.

SHOWS = [
    {
        "title": "Stranger Things",
        "recommendation_reason": None,
        "genres": ["sci-fi", "drama", "mystery"],
        "short_summary": "A group of kids uncover supernatural mysteries in their small town during the 1980s.",
        "content_rating": "TV-14",
        "average_episode_length": 55,
        "number_of_seasons": 4,
        "language": "English",
    },
    {
        "title": "Brooklyn Nine-Nine",
        "recommendation_reason": None,
        "genres": ["comedy", "crime"],
        "short_summary": "A lighthearted comedy following detectives in a New York City police precinct.",
        "content_rating": "TV-14",
        "average_episode_length": 22,
        "number_of_seasons": 8,
        "language": "English",
    },
    {
        "title": "Planet Earth",
        "recommendation_reason": None,
        "genres": ["documentary", "nature"],
        "short_summary": "A visually stunning documentary series exploring Earth's natural wonders.",
        "content_rating": "TV-G",
        "average_episode_length": 50,
        "number_of_seasons": 1,
        "language": "English",
    },
    {
        "title": "Dark",
        "recommendation_reason": None,
        "genres": ["sci-fi", "thriller", "drama"],
        "short_summary": "A complex time-travel mystery connecting families across generations in a German town.",
        "content_rating": "TV-MA",
        "average_episode_length": 60,
        "number_of_seasons": 3,
        "language": "German",
    },
    {
        "title": "The Office",
        "recommendation_reason": None,
        "genres": ["comedy"],
        "short_summary": "A mockumentary-style comedy about everyday office life and awkward coworkers.",
        "content_rating": "TV-14",
        "average_episode_length": 22,
        "number_of_seasons": 9,
        "language": "English",
    },
    {
        "title": "Avatar: The Last Airbender",
        "recommendation_reason": None,
        "genres": ["animation", "adventure", "fantasy"],
        "short_summary": "A young hero must master the elements to restore balance to a war-torn world.",
        "content_rating": "TV-Y7",
        "average_episode_length": 23,
        "number_of_seasons": 3,
        "language": "English",
    },
]


def get_all_shows():
    """Return the full static list of TV shows."""
    return SHOWS
