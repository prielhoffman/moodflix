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


  /* Load watchlist when app starts */
  useEffect(() => {
    loadWatchlist();
  }, []);


  async function loadWatchlist() {
    try {
      const data = await fetchWatchlist();
      setWatchlist(data.watchlist);
    } catch (err) {
      console.error("Failed to load watchlist");
    }
  }


  async function handleFormSubmit(preferences) {
    setIsLoading(true);
    setError(null);
    setRecommendations([]);

    try {
      const results = await recommendShows(preferences);
      setRecommendations(results);

      // Refresh watchlist after new recommendations
      await loadWatchlist();
    } catch (err) {
      setError("Something went wrong. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }


  function scrollCarousel(direction) {
    if (!carouselRef.current) return;

    const scrollAmount = 400;

    carouselRef.current.scrollBy({
      left: direction === "left" ? -scrollAmount : scrollAmount,
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
      let data;

      if (isSaved(title)) {
        data = await removeFromWatchlist(title);
      } else {
        data = await addToWatchlist(title);
      }

      setWatchlist(data.watchlist);
    } catch (err) {
      console.error("Failed to update watchlist");
    } finally {
      setSavingTitle(null);
    }
  }


  return (
    <div className="app-container">
      {!showForm ? (
        /* ---------------- Home Screen ---------------- */
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
      ) : (
        /* ---------------- Form + Results Screen ---------------- */
        <div className="form-screen">
          <button
            onClick={() => setShowForm(false)}
            className="back-button"
          >
            ← Back
          </button>

          <PreferenceForm onSubmit={handleFormSubmit} />

          {isLoading && (
            <p className="loading-text">Loading recommendations...</p>
          )}

          {error && <p className="error-text">{error}</p>}


          {!isLoading && !error && recommendations.length > 0 && (
            <div className="results-section">
              <h3>Recommended for you</h3>

              <div className="carousel-wrapper">
                <button
                  className="carousel-arrow left"
                  onClick={() => scrollCarousel("left")}
                >
                  ←
                </button>

                <div className="carousel-container" ref={carouselRef}>
                  {recommendations.map((show, index) => {
                    const saved = isSaved(show.title);

                    return (
                      <div key={index} className="poster-card">

                        {/* Save Button */}
                        <button
                          className={`save-button ${saved ? "saved" : ""}`}
                          disabled={savingTitle === show.title}
                          onClick={() => toggleSave(show.title)}
                        >
                          {saved ? "❤️ Saved" : "♡ Save"}
                        </button>


                        {/* Poster */}
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


                        {/* Card Content */}
                        <div className="card-content">
                          <h4 className="card-title">{show.title}</h4>

                          {show.tmdb_rating && (
                            <p className="card-rating">
                              ⭐ {show.tmdb_rating.toFixed(1)}
                            </p>
                          )}

                          <p className="card-summary">
                            {show.short_summary}
                          </p>

                          <p className="card-reason">
                            <strong>Why:</strong>{" "}
                            {show.recommendation_reason || "Good match for you"}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>

                <button
                  className="carousel-arrow right"
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
