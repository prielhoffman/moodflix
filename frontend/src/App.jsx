import "./App.css";

import { useEffect, useRef, useState } from "react";
import { Routes, Route, useNavigate } from "react-router-dom";

import Header from "./components/Header";
import PreferenceForm from "./components/PreferenceForm";

import {
  recommendShows,
  addToWatchlist,
  removeFromWatchlist,
  fetchWatchlist,
} from "./api/moodflixApi";

function App() {
  const [recommendations, setRecommendations] = useState([]);
  const [watchlist, setWatchlist] = useState([]); // [{ title, poster_url }]
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [savingTitle, setSavingTitle] = useState(null);

  const carouselRef = useRef(null);
  const navigate = useNavigate();

  /* Load watchlist on app startup */
  useEffect(() => {
    loadWatchlist();
  }, []);

  async function loadWatchlist() {
    try {
      const data = await fetchWatchlist();
      setWatchlist(Array.isArray(data.watchlist) ? data.watchlist : []);
    } catch (err) {
      console.error("Watchlist load failed", err);
    }
  }

  async function handleFormSubmit(preferences) {
    setIsLoading(true);
    setError(null);
    setRecommendations([]);

    try {
      const results = await recommendShows(preferences);
      setRecommendations(Array.isArray(results) ? results : []);
      await loadWatchlist();
    } catch (err) {
      console.error(err);
      setError("Something went wrong. Try again.");
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

  /* Check if show exists in watchlist */
  function isSaved(title) {
    return watchlist.some((item) => item?.title === title);
  }

  async function toggleSave(show) {
    const title = show?.title;

    if (!title) return;
    if (savingTitle) return;

    setSavingTitle(title);

    try {
      const data = isSaved(title)
        ? await removeFromWatchlist(title)
        : await addToWatchlist(show);

      setWatchlist(Array.isArray(data.watchlist) ? data.watchlist : []);
    } catch (err) {
      console.error(err);
    } finally {
      setSavingTitle(null);
    }
  }

  async function handleRemoveFromWatchlist(title) {
    try {
      const data = await removeFromWatchlist(title);
      setWatchlist(Array.isArray(data.watchlist) ? data.watchlist : []);
    } catch (err) {
      console.error("Remove failed", err);
    }
  }

  return (
    <div className="app">
      <Header />

      <main className="page-container">
        <div className="page-inner">
          <Routes>
            {/* HOME */}
            <Route
              path="/"
              element={
                <section className="hero-section">
                  <div className="hero-content">
                    <h1>MoodFlix 📺</h1>
                    <p>Tell us how you feel. We’ll tell you what to binge.</p>

                    <button
                      className="primary-button"
                      onClick={() => navigate("/recommend")}
                    >
                      Tell me what to binge
                    </button>
                  </div>
                </section>
              }
            />

            {/* RECOMMEND */}
            <Route
              path="/recommend"
              element={
                <section className="content-section">
                  <div className="content-wrapper">
                    <div className="preferences-box">
                      <PreferenceForm onSubmit={handleFormSubmit} />
                    </div>

                    {isLoading && (
                      <div className="status-center">
                        <p className="loading-text">Loading...</p>
                      </div>
                    )}

                    {error && (
                      <div className="status-center">
                        <p className="error-text">{error}</p>
                      </div>
                    )}

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

                          <div className="carousel-container" ref={carouselRef}>
                            {recommendations.map((show, i) => {
                              const saved = isSaved(show.title);

                              return (
                                <div key={i} className="poster-card">
                                  <button
                                    className={`save-button ${
                                      saved ? "saved" : ""
                                    }`}
                                    onClick={() => toggleSave(show)}
                                    disabled={savingTitle === show.title}
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
                </section>
              }
            />

            {/* WATCHLIST */}
            <Route
              path="/watchlist"
              element={
                <section className="content-section">
                  <div className="content-wrapper">
                    <h2>My Watchlist</h2>

                    {watchlist.length === 0 && (
                      <div className="empty-watchlist">
                        <p>No saved shows yet</p>
                        <p>Start adding some recommendations 📺</p>
                      </div>
                    )}

                    {watchlist.length > 0 && (
                      <div className="watchlist-grid">
                        {watchlist.map((show, i) => (
                          <div key={i} className="watchlist-card">
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

                            <h4>{show.title}</h4>

                            <button
                              className="remove-button"
                              onClick={() =>
                                handleRemoveFromWatchlist(show.title)
                              }
                            >
                              Remove
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </section>
              }
            />
          </Routes>
        </div>
      </main>
    </div>
  );
}

export default App;
