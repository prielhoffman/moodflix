import { useState } from "react";

function GuestLanding({
  onGuestSearch,
  onGuestMood,
  isLoading,
  error,
  recommendations,
  carouselRef,
  onScrollCarousel,
}) {
  const [searchQuery, setSearchQuery] = useState("");
  const [guestOver18, setGuestOver18] = useState(false);

  const guestFamilySafe = !guestOver18;

  function handleSearchSubmit(e) {
    e.preventDefault();
    onGuestSearch(searchQuery.trim());
  }

  return (
    <section className="hero-section">
      <div className="hero-content">
        <h1>MoodFlix 📺</h1>
        <p>Describe what you want to watch. We&apos;ll find something fast.</p>

        {isLoading && (
          <div className="status-center">
            <p className="loading-text">Loading...</p>
          </div>
        )}

        <form className="home-search-form" onSubmit={handleSearchSubmit}>
          <input
            type="text"
            className="home-search-input"
            placeholder="Describe what you are looking for..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Search for shows by description"
          />
          <button
            type="submit"
            className="primary-button home-search-submit"
            disabled={isLoading}
          >
            {isLoading ? "Finding…" : "Find shows"}
          </button>
        </form>

        <div className="guest-mood-buttons">
          <button
            type="button"
            className="mood-button"
            onClick={() => onGuestMood("chill", guestFamilySafe)}
            disabled={isLoading}
          >
            Chill
          </button>
          <button
            type="button"
            className="mood-button"
            onClick={() => onGuestMood("adrenaline", guestFamilySafe)}
            disabled={isLoading}
          >
            Adrenaline
          </button>
          <button
            type="button"
            className="mood-button"
            onClick={() => onGuestMood("curious", guestFamilySafe)}
            disabled={isLoading}
          >
            Curious
          </button>
        </div>

        <div className="home-age-toggle">
          <label className="home-age-label">
            <input
              type="checkbox"
              checked={guestOver18}
              onChange={(e) => setGuestOver18(e.target.checked)}
              aria-label="I am 18 or older"
            />
            <span>I am 18 or older</span>
          </label>
          <p className="home-age-hint">
            If unchecked, we&apos;ll show family-friendly recommendations only.
          </p>
        </div>

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
                {recommendations.map((show, i) => (
                    <div key={i} className="poster-card">
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
                ))}
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

export default GuestLanding;
