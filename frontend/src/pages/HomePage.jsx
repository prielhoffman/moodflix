import { useState } from "react";

const QUICK_MOODS = [
  { id: "chill", label: "😌 Chill", value: "chill" },
  { id: "adrenaline", label: "📈 Adrenaline", value: "adrenaline" },
  { id: "dark", label: "🌑 Dark", value: "dark" },
];

function HomePage({ authUser, onQuickRecommend, isLoading }) {
  const [searchQuery, setSearchQuery] = useState("");
  const [guestOver18, setGuestOver18] = useState(false);

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

  return (
    <section className="hero-section">
      <div className="hero-content">
        <h1>MoodFlix 📺</h1>
        <p>Describe what you want to watch or pick a mood. We’ll find something fast.</p>

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

        {isGuest && (
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
              If unchecked, we’ll show family-friendly recommendations only.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}

export default HomePage;
