# 🎬 MoodFlix

MoodFlix is a backend-first web application that recommends TV shows based on the user’s **mood**, **watching preferences**, and **context**.

The project is designed with clean architecture principles, focusing on separation of concerns, testability, and future extensibility toward a full Netflix-like experience.

The project was developed with the assistance of AI tools (ChatGPT) for architecture design, testing strategy, and code review.

---

## ✨ Key Features

- Mood-based TV show recommendations
- Preference-aware filtering:
  - Age & family safety
  - Binge vs short series
  - Episode length
  - Language
- Explainable recommendations (why a show was suggested)
- TMDB integration for posters and metadata
- Graceful handling of external API failures
- Fully tested recommendation logic
- React-based frontend interface

---

## 🧠 Recommendation Logic

Recommendations are generated using a multi-stage pipeline:

1. **Hard filters**
   - Age restrictions
   - Family-safe content
   - Binge / short-series preference
   - Episode length
   - Language

2. **Soft matching**
   - Preferred genres
   - Mood → genre affinity mapping
   - Mood affects ranking, not filtering

3. **Explainability**
   - Each recommendation may include a short human-readable reason explaining the match

4. **External enrichment**
   - Posters, ratings, and summaries are fetched from TMDB
   - Failures do not break recommendations

---

## 🌐 TMDB Integration

MoodFlix uses **The Movie Database (TMDB)** API to enrich recommendations with:

- Poster images
- Ratings
- Overviews
- First air date

TMDB is treated as an **external enrichment layer**, isolated from business logic.

If TMDB is unavailable or returns incomplete data, recommendations still work correctly.

---

## 🧪 Testing Strategy

The project includes comprehensive tests using `pytest`:

### Recommendation Logic Tests
- Safety rules (age, family context)
- Binge and episode length preferences
- Genre matching
- Mood-based ranking
- Recommendation reason generation

### TMDB Integration Tests
- TMDB returning no results
- Missing poster data
- Valid metadata mapping
- Network/API failures
- Ensuring enrichment does not affect core logic

All external API calls are mocked — no real network access during tests.

---

## 🗂 Project Structure

```
app/
  api.py        # FastAPI routes
  logic.py      # Recommendation engine
  data.py       # Show dataset (temporary, will be replaced by DB)
  schemas.py    # Pydantic models
  tmdb.py       # TMDB external API adapter

frontend/
  public/
  src/
    api/         # API communication
    assets/      # Images and static files
    components/  # React components
    App.jsx
    App.css
    main.jsx
    index.css

tests/
  test_logic.py # Recommendation logic tests
  test_tmdb.py  # TMDB integration tests
```

---

## 💻 Frontend

The frontend is built with **React (Vite)** and provides:

- User preference form
- Recommendation results view
- Netflix-style layout foundation
- API integration with FastAPI backend

Future UI enhancements will include carousels and personalization features.

---

## 🤖 AI-Assisted Development

This project was developed with the assistance of AI tools (ChatGPT) for:

- System design and architecture planning
- Writing and refining tests
- Code review and refactoring
- Debugging and troubleshooting
- Documentation support

All architectural and technical decisions were reviewed and validated by the developer.

---

## ⚙️ Environment Setup

MoodFlix requires a TMDB API key.

Create a `.env` file in the project root:

TMDB_API_KEY=your_tmdb_api_key_here

Install dependencies:

pip install -r requirements.txt

Run the API:

```bash
uvicorn app.api:app --reload
```

Swagger UI:

http://127.0.0.1:8000/docs

---

## 🚀 Roadmap

- Frontend UI with Netflix-style poster cards
- Carousel-based browsing
- User accounts & watch history
- Personalization based on past selections
- Database integration
- Recommendation feedback loop (“this helped / didn’t help”)

---

## 📝 Notes

- Current show data is temporary and used for logic validation
- Future versions will replace static data with a database
- The project prioritizes correctness, clarity, and extensibility over premature optimization

---

## 💡 Why this project?

MoodFlix is built as a learning and portfolio project to demonstrate:

- Clean backend architecture
- Real-world API integration
- Thoughtful testing
- Product-oriented decision making
