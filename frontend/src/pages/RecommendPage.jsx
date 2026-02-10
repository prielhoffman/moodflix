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

                        {show.tmdb_rating && <p>⭐ {show.tmdb_rating}</p>}

                        <p>{show.short_summary}</p>

                        <p>
                          <strong>Why:</strong> {show.recommendation_reason}
                        </p>
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
