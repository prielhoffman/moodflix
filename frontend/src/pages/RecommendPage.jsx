import PreferenceForm from "../components/PreferenceForm";
import { useState } from "react";

function RecommendPage({
  onSubmitPreferences,
  isLoading,
  error,
  recommendations,
  isSaved,
  onToggleSave,
  savingTitle,
}) {
  const [hasRequestedRecommendations, setHasRequestedRecommendations] = useState(false);

  function handleSubmitPreferences(preferences) {
    setHasRequestedRecommendations(true);
    onSubmitPreferences(preferences);
  }

  return (
    <section className="content-section recommend-content-section">
      <div className="recommend-page">
        <section className="page-intro-band">
          <p className="page-eyebrow">Recommendations</p>
          <h1 className="page-title">Find your next show by mood</h1>
          <p className="page-subtitle">
            Pick a mood, refine the tone, and get a focused set of shows to try next.
          </p>
        </section>

        <section className="recommend-layout">
          <aside className="recommend-controls-column">
            <div className="recommend-controls-card">
              <div className="recommend-controls-header">
                <h2>Set the mood</h2>
                <p>Choose what you feel like watching right now.</p>
              </div>
              <PreferenceForm onSubmit={handleSubmitPreferences} />
            </div>
          </aside>

          <section className="recommend-results-column">
            <div className="recommend-results-header">
              <div>
                <h2>Your picks</h2>
                <p>Up to 10 recommendations based on your current mood.</p>
              </div>
            </div>

            <div className="recommend-results-body">
              {!isLoading && !error && recommendations.length === 0 && (
                <div className="recommend-empty-state">
                  <h3>{hasRequestedRecommendations ? "No recommendations found" : "No recommendations yet"}</h3>
                  <p>
                    {hasRequestedRecommendations
                      ? "Try adjusting your mood or preferences to get a new set of picks."
                      : "Choose a mood on the left to generate a curated set of shows."}
                  </p>
                </div>
              )}

              {isLoading && (
                <div className="recommend-loading-state">
                  <p className="loading-text">Finding your next shows...</p>
                </div>
              )}

              {error && (
                <div className="recommend-error-state">
                  <p className="error-text">{error}</p>
                </div>
              )}

              {!isLoading && !error && recommendations.length > 0 && (
                <div className="recommend-results-grid">
                  {recommendations.map((show, i) => {
                    const saved = isSaved(show.title);

                    return (
                      <div key={i} className="poster-card">
                        <button
                          className={`save-button ${saved ? "saved" : ""}`}
                          onClick={() => onToggleSave(show)}
                          disabled={savingTitle === show.title}
                        >
                          {saved ? "❤️ Liked" : "♡ Like"}
                        </button>

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

                          {(show.tmdb_rating != null || show.number_of_seasons != null || show.average_episode_length != null) && (
                            <p className="rating-line">
                              {show.tmdb_rating != null && (
                                <>
                                  <span className="rating-star">★</span>{" "}
                                  {Number(show.tmdb_rating).toFixed(1)}
                                </>
                              )}
                              {(show.number_of_seasons != null || show.average_episode_length != null) && (
                                <span className="card-meta">
                                  {show.tmdb_rating != null ? " · " : ""}
                                  {[show.number_of_seasons != null && `${show.number_of_seasons} seasons`, show.average_episode_length != null && `${show.average_episode_length} min`].filter(Boolean).join(" · ")}
                                </span>
                              )}
                            </p>
                          )}

                          <p>{show.short_summary}</p>

                          {show.recommendation_reason && (
                            <div className="recommendation-reason">
                              <span className="recommendation-reason-icon" aria-hidden>💡</span>
                              <span className="recommendation-reason-label">Why: </span>
                              <span className="recommendation-reason-text">{show.recommendation_reason}</span>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </section>
        </section>
      </div>
    </section>
  );
}

export default RecommendPage;
