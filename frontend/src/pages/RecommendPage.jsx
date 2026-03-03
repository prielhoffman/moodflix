import PreferenceForm from "../components/PreferenceForm";

function RecommendPage({
  onSubmitPreferences,
  isLoading,
  error,
  recommendations,
  carouselRef,
  onScrollCarousel,
  isSaved,
  onToggleSave,
  savingTitle,
}) {
  return (
    <section className="content-section">
      <div className="content-wrapper">
        <div className="preferences-box">
          <PreferenceForm onSubmit={onSubmitPreferences} />
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
              <button className="carousel-arrow" onClick={() => onScrollCarousel("left")}>
                ←
              </button>

              <div className="carousel-container" ref={carouselRef}>
                {recommendations.map((show, i) => {
                  const saved = isSaved(show.title);

                  return (
                    <div key={i} className="poster-card">
                      <button
                        className={`save-button ${saved ? "saved" : ""}`}
                        onClick={() => onToggleSave(show)}
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

              <button className="carousel-arrow" onClick={() => onScrollCarousel("right")}>
                →
              </button>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

export default RecommendPage;
