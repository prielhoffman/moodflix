import { useState } from "react";
import HeroSection from "./guest/HeroSection";
import MoodSelector from "./guest/MoodSelector";
import GuestFooter from "./guest/GuestFooter";
import "./guest/GuestLanding.css";

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

  function handleGetRecommendations() {
    const moodSection = document.getElementById("mood-section");
    moodSection?.scrollIntoView({ behavior: "smooth" });
  }

  function handleSearchByDescription() {
    const searchSection = document.getElementById("search-section");
    searchSection?.scrollIntoView({ behavior: "smooth" });
  }

  return (
    <div className="guest-landing">
      <HeroSection
        onGetRecommendations={handleGetRecommendations}
        onSearchByDescription={handleSearchByDescription}
      />

      <MoodSelector
        onMoodSelect={(mood) => {
          // #region agent log
          fetch('http://127.0.0.1:7242/ingest/55b69589-7675-4c95-b733-981b1e330ec7',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'afab80'},body:JSON.stringify({sessionId:'afab80',location:'GuestLanding.jsx:onMoodSelect',message:'mood button clicked',data:{mood,guestFamilySafe,guestOver18},hypothesisId:'H1',timestamp:Date.now()})}).catch(()=>{});
          // #endregion
          onGuestMood(mood, guestFamilySafe);
        }}
        disabled={isLoading}
      />

      <section className="guest-search-section" id="search-section">
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
        <div className="home-age-toggle guest-age-toggle">
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
      </section>

      {(error || (isLoading && recommendations.length === 0)) && (
        <div className={`guest-status ${error ? "error" : ""}`}>
          {error || "Loading..."}
        </div>
      )}

      {!isLoading && recommendations.length > 0 && (
        <section className="guest-results">
          <h3 className="guest-results-title">Recommended for you</h3>
          <div className="guest-results-carousel" ref={carouselRef}>
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
          <div className="carousel-nav-inline">
            <button
              type="button"
              className="carousel-arrow"
              onClick={() => onScrollCarousel("left")}
            >
              ←
            </button>
            <button
              type="button"
              className="carousel-arrow"
              onClick={() => onScrollCarousel("right")}
            >
              →
            </button>
          </div>
        </section>
      )}

      <GuestFooter />
    </div>
  );
}

export default GuestLanding;
