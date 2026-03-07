import { useState } from "react";

function GuestLanding({ onQuickRecommend, isLoading, error }) {
  const [searchQuery, setSearchQuery] = useState("");
  const [guestOver18, setGuestOver18] = useState(false);

  const guestFamilySafe = !guestOver18;

  function handleSearchSubmit(e) {
    e.preventDefault();
    const trimmed = searchQuery.trim();
    onQuickRecommend({
      query: trimmed || undefined,
      mood: trimmed ? undefined : "chill",
      guestFamilySafe,
    });
  }

  return (
    <section className="hero-section">
      <div className="hero-content">
        <h1>MoodFlix 📺</h1>
        <p>Describe what you want to watch. We&apos;ll find something fast.</p>

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
      </div>
    </section>
  );
}

export default GuestLanding;
