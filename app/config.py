"""
Recommendation tuning: weights and thresholds for app/logic.py.

Adjust these values to change ranking and filtering behavior without editing
the main recommendation logic. All numeric tuning is centralized here.
"""

# --------------------------------- Recommendation defaults ---------------------------------
DEFAULT_TOP_N = 20
DEFAULT_CANDIDATE_TOP_K = 80
# When a request has a query, semantic search is used only if at least this many shows have embeddings.
# If below this (or semantic returns fewer than top_n candidates), we fall back to full DB scan / static fallback.
SEMANTIC_MIN_EMBEDDINGS = 50

# --------------------------------- Age thresholds ---------------------------------
# When watching with family, treat effective max age as this for rating rules.
FAMILY_CONTEXT_EFFECTIVE_AGE = 12
# Under this age (or family context) triggers kids/family safety and genre injection.
KIDS_CUTOFF_AGE = 13
# Below this age, block adult ratings (TV-MA, R, etc.) even when not in family mode.
ADULT_RATING_MIN_AGE = 16
# At or above this age, exclude kids/children/preschool genres unless user asked for kids content.
EXCLUDE_KIDS_GENRE_MIN_AGE = 21

# --------------------------------- Binge / series length ---------------------------------
# Short series: allow at most this many seasons.
SHORT_SERIES_MAX_SEASONS = 3
# Binge: require more than this many seasons (so 3+ seasons pass when this is 2).
# Was 3 (only 4+ passed); many TMDB shows have 1–3 seasons, so form flow collapsed to 1 result.
BINGE_MIN_SEASONS = 2

# --------------------------------- Episode length (minutes) ---------------------------------
# Short episodes: max length in minutes.
SHORT_EPISODE_MAX_MINUTES = 30
# Long episodes: min length in minutes (boundary is inclusive for long).
LONG_EPISODE_MIN_MINUTES = 30

# --------------------------------- Family context ---------------------------------
# Minimum number of candidates to aim for in family context before using relaxed fallback.
FAMILY_MIN_RESULTS = 10
# In family mode, take this many times top_n before post-enrichment filter so we still hit top_n.
FAMILY_BUFFER_MULTIPLIER = 2

# --------------------------------- Base scoring (0–1 normalized inputs) ---------------------------------
# Mood and fit matter more than raw popularity; reduce blockbuster dominance.
# base_score = RATING_WEIGHT * rating_norm + (1 - RATING_WEIGHT) * popularity_signal
RATING_WEIGHT = 0.5
# popularity_signal = POPULARITY_NORM_WEIGHT * popularity_norm + (1 - POPULARITY_NORM_WEIGHT) * vote_count_norm
POPULARITY_NORM_WEIGHT = 0.6
VOTE_COUNT_NORM_WEIGHT = 0.4

# --------------------------------- Genre scoring (optional form field) ---------------------------------
# When user selected genres and show matches: light multiplier (genre is secondary to mood).
GENRE_BASE_MULTIPLIER = 1.15
# Extra multiplier per matching genre beyond the first (capped by GENRE_EXTRA_CAP).
GENRE_EXTRA_PER_MATCH = 0.08
GENRE_EXTRA_CAP = 0.35

# --------------------------------- Mood scoring (required form field – primary ranking factor) ---------------------------------
# Mood is the core identity of MoodFlix: strong multiplier when show genres match user mood.
MOOD_BOOST_MULTIPLIER = 2.4

# --------------------------------- Ranking variety (entropy) ---------------------------------
# ± this fraction applied to final score so same mood does not always yield identical top 10.
RANKING_NOISE_FRACTION = 0.10

# --------------------------------- Mood and context boosts/penalties ---------------------------------
# Multiplier for animation/family/comedy when in family context.
FAMILY_FRIENDLY_BOOST_MULTIPLIER = 1.18
# Multiplier when kids/family context but show lacks Family/Kids/Animation genre.
KIDS_WITHOUT_FAMILY_PENALTY = 0.1
# Multiplier for talk/variety when user expects chill/happy/familiar reality.
TALK_VARIETY_PENALTY = 0.92
# When mood is DARK, penalty for shows that also have comedy or family (dramedies, light procedurals).
DARK_COMEDY_FAMILY_PENALTY = 0.4

# --------------------------------- Language scoring ---------------------------------
# Multiplier when show language is English (or marked en) and user has no foreign intent.
ENGLISH_BOOST = 1.15
# Multiplier when title/overview look English (ASCII heuristic) but language not set.
ENGLISH_HEURISTIC_BOOST = 1.12
# Multiplier for non-English when popularity and rating are below thresholds.
NON_ENGLISH_STRONG_PENALTY = 0.72
# Multiplier for non-English when popular enough (slight penalty).
NON_ENGLISH_SLIGHT_PENALTY = 0.95
# Multiplier when title/overview are not mostly ASCII.
NON_ASCII_PENALTY = 0.92
# Below these (normalized 0–1), apply NON_ENGLISH_STRONG_PENALTY instead of slight.
NON_ENGLISH_PENALTY_POPULARITY_THRESHOLD = 0.90
NON_ENGLISH_PENALTY_RATING_THRESHOLD = 0.88

# --------------------------------- English text heuristic ---------------------------------
# Min fraction of ASCII characters to consider text "English".
ENGLISH_ASCII_RATIO_MIN = 0.8

# --------------------------------- Recommendation reason (UI) ---------------------------------
# Max number of reason snippets to show per recommendation.
MAX_RECOMMENDATION_REASONS = 2
