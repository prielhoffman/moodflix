# MoodFlix 📺

**MoodFlix** is a backend service that recommends TV shows based on **how the user wants to feel**, alongside personal preferences such as age, binge preference, genres, episode length, language, and watching context.

This project is an **MVP backend application** built for learning and portfolio purposes, with a strong focus on **emotional-based recommendations**, clean architecture, explainable logic, and testability.

---

## What MoodFlix Does

* Receives user preferences (including mood) via a REST API
* Uses mood as a **soft signal** to influence ranking (not filtering)
* Applies simple, explainable recommendation rules
* Returns a ranked list of TV show recommendations
* Ensures content safety based on age and watching context

---

## Main Features

* FastAPI-based API layer
* Clear separation between API, business logic, and data
* Pydantic models for input and output validation
* Mood-driven recommendation logic (emotion as intent)
* Human-readable recommendation explanations
* Unit tests covering safety, preferences, and mood behavior
* Docker support for easy containerized execution

---

## Project Structure

```
app/
  api.py        # FastAPI API layer (input/output only)
  logic.py      # Recommendation and mood-based ranking logic
  schemas.py    # Input/output data models
  data.py       # Static TV show dataset
tests/
  test_logic.py # Unit tests for recommendation logic
```

---

## Tech Stack

* Python 3.x
* FastAPI
* Pydantic
* pytest
* Docker

---

## Running the Project

### Run Locally (Python)

1. Create and activate a virtual environment
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the API:

```bash
uvicorn app.api:app --reload
```

4. Open API docs:

```
http://127.0.0.1:8000/docs
```

---

### Run with Docker

1. Build the Docker image:

```bash
docker build -t moodflix .
```

2. Run the container:

```bash
docker run -p 8000:8000 moodflix
```

3. Access the API at:

```
http://localhost:8000/docs
```

---

## Example API Request

**Endpoint:** `POST /recommend`

```json
{
  "age": 25,
  "binge_preference": "binge",
  "preferred_genres": ["comedy", "crime"],
  "mood": "chill",
  "language_preference": "English",
  "episode_length_preference": "short",
  "watching_context": "alone"
}
```

---

## Mood-Based Recommendation Logic

MoodFlix treats **mood as emotional intent**, not a strict filter.

* Mood influences **ranking**, not eligibility
* Multiple moods are supported (e.g. chill, happy, focused, adrenaline, dark, curious)
* Mood is mapped to genres as a **soft signal**
* Recommendation explanations reflect the strongest 1–2 matching signals

Example explanation:

> “Matches your interest in comedy and feels relaxed and easy to watch.”

---

## Testing Strategy

* Core recommendation rules are covered with unit tests
* Tests verify:

  * Safety rules (age and family context)
  * Binge and episode-length preferences
  * Mood as a soft signal (does not filter shows)
  * Mood impact on ranking order
  * Honest, user-facing recommendation explanations

---

## Use of AI Tools

This project was developed with the **assistance of AI tools** as part of an iterative design and learning process.

AI was used to:

* Brainstorm feature ideas and mood modeling concepts
* Refine recommendation logic and prioritization strategies
* Improve code clarity, naming, and structure
* Design meaningful unit tests and edge-case coverage
* Review prompts, explanations, and documentation

All architectural decisions, logic design, and final code integration were **reviewed, adapted, and intentionally implemented** by the author.

---

## Notes

* TV show data is static and manually curated
* Logic is intentionally simple and explainable
* Designed to be extended in future versions:

  * External APIs (e.g. IMDb)
  * Richer mood modeling
  * Frontend UI
  * Persistence and user profiles

---

**MoodFlix** demonstrates backend fundamentals, emotional-aware recommendation logic, thoughtful use of AI-assisted development, and clean, testable architecture — in a portfolio-ready project.
