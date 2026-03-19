import { useState } from "react";
import GuestFooter from "./guest/GuestFooter";
import "./guest/GuestLanding.css";

const MOODS = [
  { id: "chill", label: "Chill" },
  { id: "adrenaline", label: "Adrenaline" },
  { id: "curious", label: "Curious" },
];

function GuestLanding({
  onGuestSearch,
  onGuestMood,
  isLoading,
  error,
  recommendations,
}) {
  const [searchQuery, setSearchQuery] = useState("");
  const [contentPreference, setContentPreference] = useState("family");

  const guestFamilySafe = contentPreference === "family";

  function handleSearchSubmit(e) {
    e.preventDefault();
    onGuestSearch(searchQuery.trim());
  }

  return (
    <div className="guest-home-page">
      <section className="page-intro-band guest-intro-band">
        <div className="guest-intro-content">
          <p className="guest-eyebrow">Mood-based TV discovery</p>
          <h1 className="guest-hero-title">Find your next show by mood</h1>
          <p className="guest-hero-subtitle">
            Pick a mood, explore recommendations, and sign in to save your favorites.
          </p>
        </div>
      </section>

      <section className="guest-discovery-layout">
        <section className="guest-controls-panel">
          <div className="guest-section-header">
            <h2>Start with a mood</h2>
            <p>Pick a mood and get a focused set of guest recommendations.</p>
          </div>

          <div className="guest-content-preference-wrap" aria-label="Guest recommendation content preference">
            <p className="guest-content-preference-label">Content preference</p>
            <div className="guest-content-preference-options" role="radiogroup" aria-label="Content preference">
              <label className={`guest-content-option ${contentPreference === "family" ? "selected" : ""}`}>
                <input
                  type="radio"
                  name="content_preference"
                  value="family"
                  checked={contentPreference === "family"}
                  onChange={() => setContentPreference("family")}
                />
                <span>Family-friendly</span>
              </label>
              <label className={`guest-content-option ${contentPreference === "adult" ? "selected" : ""}`}>
                <input
                  type="radio"
                  name="content_preference"
                  value="adult"
                  checked={contentPreference === "adult"}
                  onChange={() => setContentPreference("adult")}
                />
                <span>Adult okay</span>
              </label>
            </div>
            <p className="guest-content-preference-hint">This affects which shows we recommend.</p>
          </div>

          <div className="guest-mood-pills">
            {MOODS.map((mood) => (
              <button
                key={mood.id}
                type="button"
                className="guest-mood-pill"
                onClick={() => {
                  // #region agent log
                  fetch('http://127.0.0.1:7242/ingest/55b69589-7675-4c95-b733-981b1e330ec7',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'afab80'},body:JSON.stringify({sessionId:'afab80',location:'GuestLanding.jsx:onMoodSelect',message:'mood button clicked',data:{mood:mood.id,guestFamilySafe,contentPreference},hypothesisId:'H1',timestamp:Date.now()})}).catch(()=>{});
                  // #endregion
                  onGuestMood(mood.id, guestFamilySafe);
                }}
                disabled={isLoading}
              >
                {mood.label}
              </button>
            ))}
          </div>

          <form className="guest-search-form" onSubmit={handleSearchSubmit}>
            <input
              type="text"
              className="guest-search-input"
              placeholder="Describe what you're looking for..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              aria-label="Search for shows by description"
            />
            <button
              type="submit"
              className="guest-search-submit"
              disabled={isLoading}
            >
              {isLoading ? "Finding…" : "Find shows"}
            </button>
          </form>
        </section>

        <section className="guest-results-section">
          <div className="guest-results-header">
            <h2>Guest picks</h2>
            <p>Quick recommendations to help you explore MoodFlix before signing in.</p>
          </div>

          <div className="guest-results-body">
            {(error || (isLoading && recommendations.length === 0)) && (
              <div className={`guest-status ${error ? "error" : ""}`}>
                {error || "Loading..."}
              </div>
            )}

            {!isLoading && !error && recommendations.length === 0 && (
              <div className="guest-empty-state">
                <h3>Pick a mood to get started</h3>
                <p>Choose a mood above and MoodFlix will suggest a quick set of shows.</p>
              </div>
            )}

            {!isLoading && recommendations.length > 0 && (
              <div className="guest-results-grid">
                {recommendations.map((show, i) => (
                  <div key={show.id ?? i} className="poster-card guest-poster-card">
                    {show.poster_url ? (
                      <img
                        src={show.poster_url}
                        alt={show.title}
                        className="poster-image"
                      />
                    ) : (
                      <div className="poster-placeholder">No Image</div>
                    )}
                    <div className="card-content">
                      <h4>{show.title}</h4>
                      {(show.tmdb_rating != null ||
                        show.number_of_seasons != null ||
                        show.average_episode_length != null) && (
                        <p className="rating-line">
                          {show.tmdb_rating != null && (
                            <>
                              <span className="rating-star">★</span>{" "}
                              {Number(show.tmdb_rating).toFixed(1)}
                            </>
                          )}
                          {(show.number_of_seasons != null ||
                            show.average_episode_length != null) && (
                            <span className="card-meta">
                              {show.tmdb_rating != null ? " · " : ""}
                              {[
                                show.number_of_seasons != null &&
                                  `${show.number_of_seasons} seasons`,
                                show.average_episode_length != null &&
                                  `${show.average_episode_length} min`,
                              ]
                                .filter(Boolean)
                                .join(" · ")}
                            </span>
                          )}
                        </p>
                      )}
                      <p>{show.short_summary}</p>
                      {show.recommendation_reason && (
                        <div className="recommendation-reason">
                          <span className="recommendation-reason-icon" aria-hidden>
                            💡
                          </span>
                          <span className="recommendation-reason-label">Why: </span>
                          <span className="recommendation-reason-text">
                            {show.recommendation_reason}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>
      </section>

      <GuestFooter />
    </div>
  );
}

export default GuestLanding;
