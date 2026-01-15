# MoodFlix 📺

**MoodFlix** is a simple backend service that recommends TV shows based on user preferences such as age, binge preference, genres, content intensity (mood), episode length, language, and watching context.

This project is an **MVP backend application** built for learning and portfolio purposes, with a focus on clean structure, clear logic, and good separation of concerns.

---

## What MoodFlix Does

* Receives user preferences via a REST API
* Applies simple, explainable recommendation rules
* Returns a list of TV show recommendations
* Ensures content safety based on age and watching context

---

## Main Features

* FastAPI-based API layer
* Clear separation between API, business logic, and data
* Pydantic models for input and output validation
* Simple, explainable recommendation logic
* Unit tests for core recommendation rules
* Docker support for easy containerized execution

---

## Project Structure

```
app/
  api.py        # FastAPI API layer
  logic.py      # Recommendation logic
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
  "content_intensity": "light",
  "language_preference": "English",
  "episode_length_preference": "short",
  "watching_context": "alone"
}
```

---

## Notes

* The TV show data is static and manually curated
* The logic is intentionally simple and easy to follow
* Designed to be extended in future versions (more data, smarter ranking, persistence)

---

**MoodFlix** is built to demonstrate backend design fundamentals, clean code structure, and practical recommendation logic in a beginner-friendly way.
