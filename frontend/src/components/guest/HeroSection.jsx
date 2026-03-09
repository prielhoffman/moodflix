function HeroSection({
  headline = "Find Your Next Show in Seconds",
  subtext = "Mood-based recommendations powered by AI.",
  onGetRecommendations,
  onSearchByDescription,
}) {
  return (
    <section className="guest-hero">
      <div className="guest-hero-inner">
        <div className="guest-hero-content">
          <h1 className="guest-hero-headline">{headline}</h1>
          <p className="guest-hero-subtext">{subtext}</p>
          <div className="guest-hero-buttons">
            <button
              type="button"
              className="guest-hero-btn primary"
              onClick={onGetRecommendations}
            >
              <span className="guest-hero-btn-icon">▶</span>
              Get Recommendations
            </button>
            <button
              type="button"
              className="guest-hero-btn secondary"
              onClick={onSearchByDescription}
            >
              Search by Description
            </button>
          </div>
        </div>
        <div className="guest-hero-collage">
          <div className="guest-hero-collage-visual">
            <div className="guest-hero-collage-card guest-hero-collage-card-1" />
            <div className="guest-hero-collage-card guest-hero-collage-card-2" />
            <div className="guest-hero-collage-card guest-hero-collage-card-3" />
          </div>
        </div>
      </div>
    </section>
  );
}

export default HeroSection;
