import "./App.css";

import { useRef, useState } from "react";

// Import the PreferenceForm component
import PreferenceForm from "./components/PreferenceForm";

// Import the API helper
import { recommendShows } from "./api/moodflixApi";

function App() {
  // Controls whether we show Home screen or Form screen
  const [showForm, setShowForm] = useState(false);

  // Stores recommendation results
  const [recommendations, setRecommendations] = useState([]);

  // Loading state while waiting for backend
  const [isLoading, setIsLoading] = useState(false);

  // Error message (if something goes wrong)
  const [error, setError] = useState(null);

  // Reference to the scroll container (for arrows)
  const carouselRef = useRef(null);

  // Called when the form is submitted
  async function handleFormSubmit(preferences) {
    setIsLoading(true);
    setError(null);
    setRecommendations([]);

    try {
      const results = await recommendShows(preferences);
      setRecommendations(results);
    } catch (err) {
      setError("Something went wrong. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }

  // Scroll carousel left/right
  function scrollCarousel(direction) {
    if (!carouselRef.current) return;

    const scrollAmount = 400;

    carouselRef.current.scrollBy({
      left: direction === "left" ? -scrollAmount : scrollAmount,
      behavior: "smooth",
    });
  }

  return (
    <div className="app-container">
      {!showForm ? (
        // ---------------- Home Screen ----------------
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
        // ---------------- Form + Results Screen ----------------
        <div className="form-screen">
          {/* Back button */}
          <button
            onClick={() => setShowForm(false)}
            className="back-button"
          >
            ← Back
          </button>

          {/* Preference form */}
          <PreferenceForm onSubmit={handleFormSubmit} />

          {/* Loading state */}
          {isLoading && (
            <p className="loading-text">Loading recommendations...</p>
          )}

          {/* Error state */}
          {error && <p className="error-text">{error}</p>}

          {/* Results */}
          {!isLoading && !error && recommendations.length > 0 && (
            <div className="results-section">
              <h3>Recommended for you</h3>

              <div className="carousel-wrapper">
                {/* Left Arrow */}
                <button
                  className="carousel-arrow left"
                  onClick={() => scrollCarousel("left")}
                >
                  ←
                </button>

                {/* Scroll Container */}
                <div className="carousel-container" ref={carouselRef}>
                  {recommendations.map((show, index) => (
                    <div key={index} className="poster-card">
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

                      {/* Card content */}
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
                  ))}
                </div>

                {/* Right Arrow */}
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
