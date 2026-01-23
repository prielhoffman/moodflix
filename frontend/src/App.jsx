import "./App.css";

import { useState } from "react";

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

  // Called when the form is submitted
  async function handleFormSubmit(preferences) {
    // Reset previous state
    setIsLoading(true);
    setError(null);
    setRecommendations([]);

    try {
      // Call backend API
      const results = await recommendShows(preferences);

      // Save results in state
      setRecommendations(results);
    } catch (err) {
      // Show basic error message
      setError("Something went wrong. Please try again.");
    } finally {
      // Stop loading in all cases
      setIsLoading(false);
    }
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
          {isLoading && <p>Loading recommendations...</p>}

          {/* Error state */}
          {error && <p className="error-text">{error}</p>}

          {/* Results */}
          {!isLoading && !error && recommendations.length > 0 && (
            <div className="results-section">
              <h3>Recommended for you</h3>

              {recommendations.map((show, index) => (
                <div key={index} className="recommendation-card">
                  <h4>{show.title}</h4>

                  <p>{show.short_summary}</p>

                  <p>
                    <strong>Why:</strong>{" "}
                    {show.recommendation_reason || "Good match for you"}
                  </p>

                  <p>
                    <strong>Genres:</strong> {show.genres.join(", ")}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;
