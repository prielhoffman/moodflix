import "./App.css";

import { useEffect, useRef, useState } from "react";

import PreferenceForm from "./components/PreferenceForm";

import {
  recommendShows,
  addToWatchlist,
  removeFromWatchlist,
  fetchWatchlist,
} from "./api/moodflixApi";

function App() {
  const [showForm, setShowForm] = useState(false);
  const [recommendations, setRecommendations] = useState([]);
  const [watchlist, setWatchlist] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [savingTitle, setSavingTitle] = useState(null);

  const carouselRef = useRef(null);

  useEffect(() => {
    loadWatchlist();
  }, []);

  async function loadWatchlist() {
    try {
      const data = await fetchWatchlist();
      setWatchlist(data.watchlist);
    } catch {
      console.error("Watchlist load failed");
    }
  }

  async function handleFormSubmit(preferences) {
    setIsLoading(true);
    setError(null);

    try {
      const results = await recommendShows(preferences);
      setRecommendations(results);
      await loadWatchlist();
    } catch {
      setError("Something went wrong.");
    } finally {
      setIsLoading(false);
    }
  }

  function scrollCarousel(direction) {
    if (!carouselRef.current) return;

    carouselRef.current.scrollBy({
      left: direction === "left" ? -400 : 400,
      behavior: "smooth",
    });
  }

  function isSaved(title) {
    return watchlist.includes(title);
  }

  async function toggleSave(title) {
    if (savingTitle) return;

    setSavingTitle(title);

    try {
      const data = isSaved(title)
        ? await removeFromWatchlist(title)
        : await addToWatchlist(title);

      setWatchlist(data.watchlist);
    } finally {
      setSavingTitle(null);
    }
  }

  return (
    <div className="app-container">

      {/* ---------------- HOME ---------------- */}
      {!showForm && (
        <div className="home-wrapper">
          <div className="home-screen">
            <h1>MoodFlix 📺</h1>

            <p>Tell us how you feel. We’ll tell you what to binge.</p>

            <button
              onClick={() => setShowForm(true)}
              className="primary-button"
            >
              Tell me what to binge
            </button>
          </div>
        </div>
      )}

      {/* ---------------- FORM + RESULTS ---------------- */}
      {showForm && (
        <div className="content-wrapper">

          <button
            onClick={() => setShowForm(false)}
            className="back-button"
          >
            ← Back
          </button>

          <PreferenceForm onSubmit={handleFormSubmit} />

          {isLoading && (
            <p className="loading-text">Loading...</p>
          )}

          {error && <p className="error-text">{error}</p>}

          {!isLoading && recommendations.length > 0 && (
            <div className="results-section">

              <h3>Recommended for you</h3>

              <div className="carousel-wrapper">

                <button
                  className="carousel-arrow"
                  onClick={() => scrollCarousel("left")}
                >
                  ←
                </button>

                <div
                  className="carousel-container"
                  ref={carouselRef}
                >
                  {recommendations.map((show, i) => {
                    const saved = isSaved(show.title);

                    return (
                      <div key={i} className="poster-card">

                        <button
                          className={`save-button ${saved ? "saved" : ""}`}
                          onClick={() => toggleSave(show.title)}
                        >
                          {saved ? "❤️ Saved" : "♡ Save"}
                        </button>

                        {show.poster_url ? (
                          <img
                            src={show.poster_url}
                            alt={show.title}
                            className="poster-image"
                          />
                        ) : (
                          <div className="poster-placeholder">
                            No Image
                          </div>
                        )}

                        <div className="card-content">

                          <h4>{show.title}</h4>

                          {show.tmdb_rating && (
                            <p>⭐ {show.tmdb_rating}</p>
                          )}

                          <p>{show.short_summary}</p>

                          <p>
                            <strong>Why:</strong>{" "}
                            {show.recommendation_reason}
                          </p>

                        </div>
                      </div>
                    );
                  })}
                </div>

                <button
                  className="carousel-arrow"
                  onClick={() => scrollCarousel("right")}
                >
                  →
                </button>

              </div>
            </div>
          )}
        </div>
      )}

    </div>
  );
}

export default App;
