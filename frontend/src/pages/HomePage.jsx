import { useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import PreferenceForm from "../components/PreferenceForm";

const QUICK_MOODS = [
  { id: "chill", label: "😌 Chill", value: "chill" },
  { id: "adrenaline", label: "📈 Adrenaline", value: "adrenaline" },
  { id: "dark", label: "🌑 Dark", value: "dark" },
];

function HomePage({
  authUser,
  onQuickRecommend,
  isLoading,
  onSubmitPreferences,
  error,
  recommendations,
  carouselRef,
  onScrollCarousel,
  isSaved,
  onToggleSave,
  savingTitle,
}) {
  const [searchQuery, setSearchQuery] = useState("");
  const [guestOver18, setGuestOver18] = useState(false);
  const location = useLocation();

  console.log("VERSION 2.0 - UPDATED", { authUser: !!authUser });

  const viewMode = useMemo(() => {
    const params = new URLSearchParams(location.search);
    const forced = (params.get("view") || "").toLowerCase();
    if (forced === "search" || forced === "prefs") return forced;
    return authUser ? "prefs" : "search";
  }, [location.pathname, location.search, authUser]);

  const isGuest = !authUser;
  const guestFamilySafe = isGuest ? !guestOver18 : undefined;

  function handleSearchSubmit(e) {
    e.preventDefault();
    const trimmed = searchQuery.trim();
    onQuickRecommend({
      query: trimmed || undefined,
      mood: trimmed ? undefined : "chill",
      guestFamilySafe,
    });
  }

  function handleMoodClick(moodValue) {
    onQuickRecommend({
      mood: moodValue,
      guestFamilySafe,
    });
  }

  /* Semantic Search / hero view (even when logged in) */
  if (viewMode === "search") {
    console.log("Rendering Semantic Search view");

    const showGuestAgeToggle = !authUser;

    return (
      <section className="hero-section" data-homepage-version="2.1">
        {/* VERSION 2.1 - HomePage unified view mode (search) */}
        <div className="hero-content">
          <h1>MoodFlix 📺</h1>
          <p>Describe what you want to watch or pick a mood. We'll find something fast.</p>

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

          <div className="home-moods">
            <span className="home-moods-label">Quick mood:</span>
            <div className="home-moods-buttons">
              {QUICK_MOODS.map(({ id, label, value }) => (
                <button
                  key={id}
                  type="button"
                  className="home-mood-btn"
                  onClick={() => handleMoodClick(value)}
                  disabled={isLoading}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {showGuestAgeToggle && (
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
                If unchecked, we'll show family-friendly recommendations only.
              </p>
            </div>
          )}
        </div>
      </section>
    );
  }

  /* Preferences / recommendations view */
  if (authUser) {
    return (
      <section className="content-section" data-homepage-version="2.1">
        {/* VERSION 2.1 - HomePage unified view mode (prefs) */}
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

                          {show.tmdb_rating != null && (
                            <p className="rating-line">
                              <span className="rating-star">★</span>{" "}
                              {Number(show.tmdb_rating).toFixed(1)}
                            </p>
                          )}

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

  // Guest fallback (should only happen for / without authUser)
  console.log("Rendering Semantic Search view");
  return (
    <section className="hero-section" data-homepage-version="2.1">
      {/* VERSION 2.1 - HomePage unified view mode (search) */}
      <div className="hero-content">
        <h1>MoodFlix 📺</h1>
        <p>Describe what you want to watch or pick a mood. We'll find something fast.</p>

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

        <div className="home-moods">
          <span className="home-moods-label">Quick mood:</span>
          <div className="home-moods-buttons">
            {QUICK_MOODS.map(({ id, label, value }) => (
              <button
                key={id}
                type="button"
                className="home-mood-btn"
                onClick={() => handleMoodClick(value)}
                disabled={isLoading}
              >
                {label}
              </button>
            ))}
          </div>
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
            If unchecked, we'll show family-friendly recommendations only.
          </p>
        </div>
      </div>
    </section>
  );
}

export default HomePage;
